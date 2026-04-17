"""FAISS-backed vector storage for memory embeddings (legacy local mode)."""

from __future__ import annotations

from typing import Iterable

import faiss
import numpy as np


class VectorStore:
    """Simple in-memory FAISS vector store.

    This store keeps:
    - a FAISS `IndexFlatIP` index for similarity search
    - a Python list that maps FAISS row positions to memory IDs
    """

    def __init__(self, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be a positive integer")

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self._index_to_memory_id: list[str] = []

    def add(self, memory_id: str, embedding: Iterable[float]) -> None:
        if not memory_id:
            raise ValueError("memory_id must not be empty")

        vector = self._to_vector(embedding)
        self.index.add(vector)
        self._index_to_memory_id.append(memory_id)

    def search(self, embedding: Iterable[float], top_k: int = 5) -> list[tuple[str, float]]:
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        if self.index.ntotal == 0:
            return []

        vector = self._to_vector(embedding)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(vector, k)

        results: list[tuple[str, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue
            memory_id = self._index_to_memory_id[idx]
            results.append((memory_id, float(score)))
        return results

    def _to_vector(self, embedding: Iterable[float]) -> np.ndarray:
        vector = np.asarray(list(embedding), dtype=np.float32).reshape(1, -1)
        if vector.shape[1] != self.dimension:
            raise ValueError(
                f"embedding dimension mismatch: expected {self.dimension}, got {vector.shape[1]}"
            )
        faiss.normalize_L2(vector)
        return vector

