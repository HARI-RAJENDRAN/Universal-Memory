"""Environment-driven settings."""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Minimal settings for DB and API (no paid services)."""

    def __init__(self) -> None:
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://mem0:mem0@localhost:5432/unimem",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

