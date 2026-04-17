"""One-time DB setup: enable pgvector and create tables via SQLAlchemy."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from unimem.db.base import Base
from unimem.db.session import get_engine

logger = logging.getLogger(__name__)


def ensure_pgvector_extension() -> None:
    """Create `vector` extension if the DB role allows (superuser or pre-granted)."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        logger.info("pgvector extension ensured")
    except SQLAlchemyError as exc:
        logger.warning(
            "Could not CREATE EXTENSION vector (may already exist or need superuser): %s",
            exc,
        )


def create_all_tables() -> None:
    """Create ORM tables (requires extension for vector type)."""
    # Import models so they register on Base.metadata
    from unimem.models import memory as _memory  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate existing databases to attach context safely
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE memory ADD COLUMN IF NOT EXISTS context TEXT NOT NULL DEFAULT 'general';"))
            conn.execute(text("ALTER TABLE memory ADD COLUMN IF NOT EXISTS trust_score FLOAT NOT NULL DEFAULT 1.0;"))
        logger.info("SQL schema auto-migrated (context & trust_score columns ensured)")
    except SQLAlchemyError as exc:
        logger.warning("Could not auto-migrate schema columns (ignore if they exist): %s", exc)
        
    logger.info("SQLAlchemy tables created (if missing)")

