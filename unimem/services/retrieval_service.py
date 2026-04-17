"""Semantic retrieval engine scoring and ranking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from unimem.config.config import MemoryConfig
from unimem.models.memory import Memory
from unimem.retrieval.scoring import ScoredMemory, cosine_similarity_from_distance, normalize_recency, normalize_frequency
from unimem.core.logger import get_logger
from unimem.embeddings.embedder import embed
from unimem.extractor.extractor import detect_context

logger = get_logger(__name__)

# Candidate pool size before re-ranking with composite score
VECTOR_CANDIDATE_LIMIT = 50

class RetrievalService:
    """Handles vector search, re-ranking, and context augmentation logic."""

    def __init__(
        self,
        session: Session,
        config: MemoryConfig,
        embed_fn=None
    ) -> None:
        self._session = session
        self._config = config
        self._embed = embed_fn or embed

    def search_memories(
        self,
        user_id: str,
        query: str,
        *,
        bump_usage: bool = True,
        debug: bool = False,
    ) -> list[ScoredMemory]:
        """Fetch candidates from vector store and composite score them."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id must not be empty")
        if not query.strip():
            raise ValueError("query must not be empty")

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Determine explicit Context routing constraints
        query_context = detect_context(query)
        logger.info("query_context_detected context=%s query=%s", query_context, query)
        
        try:
            qvec = self._embed(query)
            dist_expr = Memory.embedding.cosine_distance(qvec)
            
            # Foundational Filters
            base_filters = [
                Memory.user_id == user_id.strip(),
                Memory.trust_score >= self._config.trust_retrieval_threshold,
                (Memory.use_count >= 2) | (Memory.created_at >= thirty_days_ago)
            ]
            
            if query_context != "general":
                strict_filters = base_filters + [Memory.context == query_context]
                stmt = (
                    select(Memory, dist_expr.label("dist"))
                    .where(*strict_filters)
                    .order_by(dist_expr.asc())
                    .limit(VECTOR_CANDIDATE_LIMIT)
                )
                rows = self._session.execute(stmt).all()
                if not rows:
                    logger.info("fallback_trigger user_id=%s missing_context=%s", user_id, query_context)
                    stmt = (
                        select(Memory, dist_expr.label("dist"))
                        .where(*base_filters)
                        .order_by(dist_expr.asc())
                        .limit(VECTOR_CANDIDATE_LIMIT)
                    )
                    rows = self._session.execute(stmt).all()
            else:
                stmt = (
                    select(Memory, dist_expr.label("dist"))
                    .where(*base_filters)
                    .order_by(dist_expr.asc())
                    .limit(VECTOR_CANDIDATE_LIMIT)
                )
                rows = self._session.execute(stmt).all()
        except SQLAlchemyError:
            logger.exception("semantic_search_failed user_id=%s", user_id)
            raise

        ranked: list[ScoredMemory] = []
        for mem, dist in rows:
            dist_f = float(dist)
            sim = cosine_similarity_from_distance(dist_f)
            
            # Apply dynamic config weights
            rec = normalize_recency(mem.created_at, now=now)
            freq = normalize_frequency(mem.use_count)
            score = (
                self._config.weight_similarity * sim
                + self._config.weight_recency * rec
                + self._config.weight_frequency * freq
            )

            ranked.append(
                ScoredMemory(
                    memory_id=str(mem.id),
                    context=getattr(mem, 'context', 'general'),
                    content=mem.content,
                    memory_type=mem.type,
                    similarity=sim,
                    recency_score=rec,
                    frequency_score=freq,
                    final_score=score,
                    cosine_distance=dist_f,
                )
            )
            
            if debug:
                print("\n[DEBUG]")
                print(f"Memory: {mem.content}")
                print(f"Similarity: {sim:.4f}")
                print(f"Recency: {rec:.4f}")
                print(f"Frequency: {freq:.4f}")
                print(f"Final Score: {score:.4f}")

        ranked.sort(key=lambda x: x.final_score, reverse=True)
        top = ranked[: self._config.top_k]

        logger.info(
            "semantic_retrieval user_id=%s returned=%s top_scores=%s",
            user_id,
            len(top),
            [round(t.final_score, 4) for t in top],
        )

        if bump_usage and top:
            ids = [UUID(s.memory_id) for s in top]
            self._increment_usage(ids)
            try:
                self._session.commit()
            except SQLAlchemyError:
                self._session.rollback()
                logger.exception("usage_bump_failed user_id=%s", user_id)
                raise

        return top

    def explain_retrieval(self, query: str, user_id: str) -> list[dict]:
        """Runs the search transparently identifying algorithmic priority."""
        memories = self.search_memories(user_id=user_id, query=query, bump_usage=False)
        explanations = []
        for m in memories:
            highest_score = max(
                (m.similarity * self._config.weight_similarity, "Similarity"),
                (m.recency_score * self._config.weight_recency, "Recency"),
                (m.frequency_score * self._config.weight_frequency, "Frequency")
            )
            explanations.append({
                "content": m.content,
                "similarity": round(m.similarity, 4),
                "recency_score": round(m.recency_score, 4),
                "frequency_score": round(m.frequency_score, 4),
                "final_score": round(m.final_score, 4),
                "reasoning": f"Primary factor: {highest_score[1]} (Weighted contribution: {round(highest_score[0], 4)})"
            })
        return explanations

    def _increment_usage(self, ids: list[UUID]) -> None:
        """Increment use_count and touch last_used_at for retrieved data points."""
        if not ids:
            return
        now = datetime.now(timezone.utc)
        rows = self._session.scalars(select(Memory).where(Memory.id.in_(ids))).all()
        for m in rows:
            m.use_count = (m.use_count or 0) + 1
            m.last_used_at = now
