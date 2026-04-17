"""Memory persistence, deduplication, and vector embeddings storage."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from unimem.embeddings.embedder import embed
from unimem.extractor.extractor import Extractor, SimpleMemoryExtractor, is_suspicious
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

    def should_store(self, text: str) -> bool:
        """Filter memory input layer."""
        t = text.strip().lower()
        if not t or len(t) < 10:
            return False
        trivial = {"ok", "yes", "no", "thanks", "cool", "fine"}
        if t in trivial:
            return False
        return True

    def merge_memory(self, old: str, new: str) -> str:
        """Simple rule-based merge."""
        if old.lower() == new.lower():
            return old
        return f"{old}. {new}"

    def add_memory(self, user_id: str, text: str) -> list[dict[str, Any]]:
        """Extract items, dedupe by vector similarity, insert or update."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id must not be empty")
        if not text or not text.strip():
            raise ValueError("text must not be empty")

        if not self.should_store(text):
            print(f"[DEBUG] Skipped memory (filtered): {text}")
            logger.info("memory_skipped_filtered user_id=%s text=%s", user_id, text)
            return []
            
        # [Phase 2] Security Heuristics Gate
        if is_suspicious(text):
            print(f"[SECURITY] Blocked suspicious memory: {text}")
            logger.warning("[SECURITY] blocked suspicious memory user_id=%s text=%s", user_id, text)
            return []
            
        # [Phase 3.1] Rate Limit Engine
        now = datetime.now(timezone.utc)
        one_min_ago = now - timedelta(minutes=1)
        stmt = select(func.count(Memory.id)).where(
            Memory.user_id == user_id.strip(),
            Memory.created_at >= one_min_ago
        )
        count_recent = self._session.execute(stmt).scalar() or 0
        if count_recent >= self._config.max_memory_per_minute:
            print(f"[SECURITY] Rate limit exceeded. Dropping request.")
            logger.warning("[SECURITY] rate limit exceeded user_id=%s", user_id)
            return []

        saved: list[dict[str, Any]] = []
        try:
            items = self._extractor.extract(text)
            for item in items:
                content = (item.get("content") or "").strip()
                if not content:
                    continue

                mem_type = _normalize_memory_type(str(item.get("type") or "preference"))
                mem_context = str(item.get("context") or "general")
                vector = self._embed(content)

                merged = self._handle_existing_similar(
                    user_id=user_id,
                    embedding=vector,
                    new_content=content,
                    new_context=mem_context,
                )
                if merged is not None:
                    saved.append(self._row_to_dict(merged))
                    continue

                row = Memory(
                    user_id=user_id.strip(),
                    type=mem_type,
                    context=mem_context,
                    trust_score=0.5,
                    content=content,
                    embedding=vector,
                    last_used_at=datetime.now(timezone.utc),
                    use_count=1,
                )
                self._session.add(row)
                self._session.flush()
                print(f"[DEBUG] Stored memory: {content}")
                logger.info(
                    "memory_added user_id=%s memory_id=%s type=%s",
                    user_id,
                    row.id,
                    mem_type,
                )
                saved.append(self._row_to_dict(row))
            self._session.commit()
            
            # Enforce capacity
            self._enforce_max_limit(user_id)
            
        except SQLAlchemyError:
            self._session.rollback()
            logger.exception("memory_add_failed user_id=%s", user_id)
            raise
        return saved

    def _handle_existing_similar(
        self,
        *,
        user_id: str,
        embedding: list[float],
        new_content: str,
        new_context: str,
    ) -> Memory | None:
        """Return updated row if a sufficiently similar memory exists for this user."""
        closest = self._closest_neighbor(user_id, embedding)
        if closest is None:
            return None

        memory, distance = closest
        similarity = cosine_similarity_from_distance(distance)
        if similarity < self._config.dedup_threshold:
            return None

        old_content = memory.content
        if similarity > 0.95 or old_content.lower() == new_content.lower():
            print(f"[DEBUG] Merged memory (bumped use count): {old_content}")
            logger.info("memory_updated_usage user_id=%s memory_id=%s", user_id, memory.id)
            memory.last_used_at = datetime.now(timezone.utc)
            memory.use_count = (memory.use_count or 0) + 1
            memory.trust_score = min(1.0, float(getattr(memory, 'trust_score', 0.5)) + 0.2)
            return memory

        merged_content = self.merge_memory(old_content, new_content)
        print(f"[DEBUG] Merged memory (content combined): {merged_content}")
        logger.info("memory_merged_content user_id=%s memory_id=%s", user_id, memory.id)
            
        memory.content = merged_content
        memory.context = new_context
        memory.embedding = embedding
        memory.last_used_at = datetime.now(timezone.utc)
        memory.use_count = (memory.use_count or 0) + 1
        memory.trust_score = min(1.0, float(getattr(memory, 'trust_score', 0.5)) + 0.2)
        return memory

    def _enforce_max_limit(self, user_id: str) -> None:
        """Enforces limits using recency/frequency scoring."""
        stmt = select(Memory).where(Memory.user_id == user_id.strip())
        rows = self._session.scalars(stmt).all()
        if len(rows) <= self._config.max_memories_per_user:
            return
            
        now = datetime.now(timezone.utc)
        def pop_score(m: Memory) -> float:
            age_days = (now - m.created_at).total_seconds() / 86400
            freq = m.use_count or 1
            return freq - (age_days * 0.1)

        rows.sort(key=pop_score, reverse=True)
        to_delete = rows[self._config.max_memories_per_user:]
        for drop_mem in to_delete:
            self._session.delete(drop_mem)
            logger.info("memory_deleted_limit_exceeded memory_id=%s", drop_mem.id)
        self._session.commit()

    def cleanup_memory(self, user_id: str) -> int:
        """Periodic auto-cleanup. Delete if use_count < 2 AND > 30 days old."""
        stmt = select(Memory).where(Memory.user_id == user_id.strip())
        rows = self._session.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        deleted_count = 0
        for m in rows:
            age_days = (now - m.created_at).total_seconds() / 86400
            if (m.use_count or 1) < 2 and age_days > 30:
                self._session.delete(m)
                deleted_count += 1
                logger.info("memory_deleted_decay memory_id=%s", m.id)
        
        if deleted_count > 0:
            self._session.commit()
            print(f"[DEBUG] Cleanup purged {deleted_count} decayed memories.")
        return deleted_count

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
            "context": getattr(m, 'context', 'general'),
            "trust_score": getattr(m, 'trust_score', 1.0),
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
            "use_count": m.use_count,
        }

    @staticmethod
    def _row_to_public_dict(m: Memory) -> dict[str, Any]:
        return MemoryService._row_to_dict(m)
