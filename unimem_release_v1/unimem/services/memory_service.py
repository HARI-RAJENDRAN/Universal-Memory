"""Memory persistence, deduplication, and vector embeddings storage."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from unimem.embeddings.embedder import embed
from unimem.extractor.extractor import Extractor, SimpleMemoryExtractor
from unimem.models.memory import Memory
from unimem.retrieval.scoring import cosine_similarity_from_distance
from unimem.core.logger import get_logger
from unimem.config.config import MemoryConfig

logger = get_logger(__name__)


def _normalize_memory_type(raw: str) -> str:
    if raw == "text":
        return "preference"
    return raw or "preference"


class MemoryService:
    """PostgreSQL + pgvector-backed memory creation and management."""

    def __init__(
        self,
        session: Session,
        config: MemoryConfig,
        embed_fn: Callable[[str], list[float]] | None = None,
        extractor: Extractor | None = None,
    ) -> None:
        self._session = session
        self._config = config
        self._embed = embed_fn or embed
        self._extractor = extractor or SimpleMemoryExtractor()

    def add_memory(self, user_id: str, text: str) -> list[dict[str, Any]]:
        """Extract items, dedupe by vector similarity, insert or update."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id must not be empty")
        if not text or not text.strip():
            raise ValueError("text must not be empty")

        saved: list[dict[str, Any]] = []
        try:
            items = self._extractor.extract(text)
            for item in items:
                content = (item.get("content") or "").strip()
                if not content:
                    continue

                mem_type = _normalize_memory_type(str(item.get("type") or "preference"))
                vector = self._embed(content)

                merged = self._merge_if_similar(
                    user_id=user_id,
                    embedding=vector,
                    new_content=content,
                )
                if merged is not None:
                    logger.info(
                        "memory_updated_dedup user_id=%s memory_id=%s",
                        user_id,
                        merged.id,
                    )
                    saved.append(self._row_to_dict(merged))
                    continue

                row = Memory(
                    user_id=user_id.strip(),
                    type=mem_type,
                    content=content,
                    embedding=vector,
                    last_used_at=datetime.now(timezone.utc),
                    use_count=1,
                )
                self._session.add(row)
                self._session.flush()
                logger.info(
                    "memory_added user_id=%s memory_id=%s type=%s",
                    user_id,
                    row.id,
                    mem_type,
                )
                saved.append(self._row_to_dict(row))
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            logger.exception("memory_add_failed user_id=%s", user_id)
            raise
        return saved

    def _merge_if_similar(
        self,
        *,
        user_id: str,
        embedding: list[float],
        new_content: str,
    ) -> Memory | None:
        """Return updated row if a sufficiently similar memory exists for this user."""
        closest = self._closest_neighbor(user_id, embedding)
        if closest is None:
            return None

        memory, distance = closest
        similarity = cosine_similarity_from_distance(distance)
        if similarity < self._config.dedup_threshold:
            return None

        memory.content = new_content
        memory.embedding = embedding
        memory.last_used_at = datetime.now(timezone.utc)
        memory.use_count = (memory.use_count or 0) + 1  # Increment use_count
        return memory

    def _closest_neighbor(
        self,
        user_id: str,
        embedding: list[float],
    ) -> tuple[Memory, float] | None:
        dist_expr = Memory.embedding.cosine_distance(embedding)
        stmt = (
            select(Memory, dist_expr.label("dist"))
            .where(Memory.user_id == user_id.strip())
            .order_by(dist_expr.asc())
            .limit(1)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        return row[0], float(row[1])

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a specific memory belonging to a user."""
        try:
            mem_uuid = UUID(memory_id)
            stmt = select(Memory).where(
                Memory.id == mem_uuid, Memory.user_id == user_id.strip()
            )
            row = self._session.scalars(stmt).first()
            if not row:
                return False

            self._session.delete(row)
            self._session.commit()
            logger.info("memory_deleted user_id=%s memory_id=%s", user_id, memory_id)
            return True
        except ValueError:
            # Invalid UUID
            return False
        except SQLAlchemyError:
            self._session.rollback()
            logger.exception("memory_delete_failed user_id=%s memory_id=%s", user_id, memory_id)
            raise

    def list_user_memories(self, user_id: str) -> list[dict[str, Any]]:
        """All memories for a user (no embedding), newest first."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id must not be empty")

        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id.strip())
            .order_by(Memory.created_at.desc())
        )
        try:
            rows = self._session.scalars(stmt).all()
        except SQLAlchemyError:
            logger.exception("memory_list_failed user_id=%s", user_id)
            raise

        return [self._row_to_public_dict(m) for m in rows]

    @staticmethod
    def _row_to_dict(m: Memory) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": m.user_id,
            "type": m.type,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
            "use_count": m.use_count,
        }

    @staticmethod
    def _row_to_public_dict(m: Memory) -> dict[str, Any]:
        return MemoryService._row_to_dict(m)
