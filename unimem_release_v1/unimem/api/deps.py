"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from unimem.core.memory_client import MemoryClient
from unimem.db.session import get_db
from unimem.services.memory_service import MemoryService


def get_memory_service(db: Session = Depends(get_db)) -> MemoryService:
    return MemoryService(db)


def get_memory_client(db: Session = Depends(get_db)) -> MemoryClient:
    return MemoryClient(db)

