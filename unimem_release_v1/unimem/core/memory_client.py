"""Main public client: Orchestrates semantic retrieval, persistence, and contextual LLM generation."""

from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from unimem.config.config import MemoryConfig
from unimem.embeddings.embedder import embed
from unimem.extractor.extractor import Extractor, SimpleMemoryExtractor
from unimem.llm.local_llm import LLMClient, LocalLLMClient
from unimem.services.memory_service import MemoryService
from unimem.services.retrieval_service import RetrievalService
from unimem.services.llm_service import LLMService


class MemoryClient:
    """High-level facade API: add, search, chat, delete, list — backed by modular services."""

    def __init__(
        self,
        db: Session,
        config: MemoryConfig | None = None,
        embed_fn=None,
        extractor: Extractor | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.config = config or MemoryConfig()
        
        self._memory_service = MemoryService(
            session=db,
            config=self.config,
            embed_fn=embed_fn,
            extractor=extractor
        )
        self._retrieval_service = RetrievalService(
            session=db,
            config=self.config,
            embed_fn=embed_fn
        )
        self._llm_service = LLMService(
            llm_client=llm_client or LocalLLMClient()
        )

    def add(self, text: str, user_id: str) -> list[dict[str, Any]]:
        """Persist structured intelligence for `user_id` (auto-deduplicated)."""
        return self._memory_service.add_memory(user_id=user_id, text=text)

    def delete(self, memory_id: str, user_id: str) -> bool:
        """Removes a specific memory data point."""
        return self._memory_service.delete_memory(memory_id=memory_id, user_id=user_id)

    def search(self, query: str, user_id: str) -> list[str]:
        """Perform a semantic search enriched with historical frequency/recency scoring."""
        scored_memories = self._retrieval_service.search_memories(
            user_id=user_id,
            query=query,
            bump_usage=True,
        )
        return [m.content for m in scored_memories]

    def get_memories(self, user_id: str) -> list[dict[str, Any]]:
        """List all intelligence elements for a user."""
        return self._memory_service.list_user_memories(user_id)

    def chat(self, query: str, user_id: str) -> str:
        """Perform context-aware generation using the semantic retrieval engine."""
        relevant_context = self.search(query=query, user_id=user_id)
        return self._llm_service.generate_contextual_response(
            query=query, 
            context_items=relevant_context
        )
