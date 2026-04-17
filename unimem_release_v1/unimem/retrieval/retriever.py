"""Memory retrieval pipeline (legacy local FAISS + SQLite)."""

from __future__ import annotations

from collections.abc import Callable

from unimem.storage.kv_store import KVStore
from unimem.storage.vector_store import VectorStore


class Retriever:
    """Retrieve relevant user memories for a query (legacy local mode)."""

    def __init__(
        self,
        vector_store: VectorStore,
        kv_store: KVStore,
        embed_fn: Callable[[str], list[float]],
    ) -> None:
        self.vector_store = vector_store
        self.kv_store = kv_store
        self.embed_fn = embed_fn

    def retrieve(self, query: str, user_id: str, top_k: int = 5) -> list[str]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not user_id:
            raise ValueError("user_id must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        query_embedding = self.embed_fn(query)
        search_results = self.vector_store.search(query_embedding, top_k=top_k * 3)
        if not search_results:
            return []

        memory_ids = [memory_id for memory_id, _score in search_results]
        memories = self.kv_store.get_memories_by_ids(memory_ids)

        relevant_texts: list[str] = []
        for memory in memories:
            if memory["user_id"] != user_id:
                continue
            relevant_texts.append(memory["content"])
            if len(relevant_texts) >= top_k:
                break

        return relevant_texts

