"""Rank memories using similarity, recency, and usage frequency."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Normalize age into [0, 1], where 1 = brand new
RECENCY_WINDOW = timedelta(days=30)

# Clamp frequency to this use_count for normalization
FREQUENCY_CAP = 100

@dataclass(frozen=True)
class ScoredMemory:
    """One ranked candidate."""

    memory_id: str
    content: str
    memory_type: str
    score: float
    similarity: float
    cosine_distance: float


def cosine_similarity_from_distance(cosine_distance: float) -> float:
    """pgvector cosine distance d maps to similarity s = 1 - d (for normalized vectors)."""
    return max(0.0, min(1.0, 1.0 - float(cosine_distance)))


def normalize_recency(created_at: datetime, *, now: datetime | None = None) -> float:
    """Higher when `created_at` is closer to now."""
    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age = now - created_at
    if age <= timedelta(0):
        return 1.0
    ratio = age.total_seconds() / RECENCY_WINDOW.total_seconds()
    return max(0.0, 1.0 - min(1.0, ratio))


def normalize_frequency(use_count: int) -> float:
    """Map use_count into [0, 1]."""
    return max(0.0, min(1.0, float(use_count) / float(FREQUENCY_CAP)))
