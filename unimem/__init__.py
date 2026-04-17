"""Unimem: server-ready unified memory layer (PostgreSQL + pgvector + Ollama)."""

from unimem.core.memory_client import MemoryClient
from unimem.config.config import MemoryConfig

__all__ = ["MemoryClient", "MemoryConfig"]

