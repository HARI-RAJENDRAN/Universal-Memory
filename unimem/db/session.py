"""Engine and session factory."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from unimem.config.settings import get_settings
from unimem.db.base import Base

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def init_engine(database_url: str | None = None) -> None:
    """Create global engine and session factory (call once at startup)."""
    global _engine, _SessionLocal
    url = database_url or get_settings().database_url
    _engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine():
    if _engine is None:
        init_engine()
    return _engine  # type: ignore[return-value]


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal  # type: ignore[return-value]


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request (caller commits)."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()

