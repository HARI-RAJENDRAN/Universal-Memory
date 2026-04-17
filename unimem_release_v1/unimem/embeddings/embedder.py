"""Embedding utilities powered by sentence-transformers.

This module exposes a single public function, `embed`, that turns text into
an embedding vector. The model is loaded lazily and cached globally so it is
initialized only once per process.
"""

from __future__ import annotations

from threading import Lock

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

_MODEL: SentenceTransformer | None = None
_MODEL_LOCK = Lock()


def _get_model() -> SentenceTransformer:
    """Return a shared SentenceTransformer instance.

    Uses thread-safe lazy initialization to avoid repeated model loads.
    """
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def embed(text: str) -> list[float]:
    """Generate an embedding vector for a single text input.

    Args:
        text: Input text to embed.

    Returns:
        A dense embedding vector as a Python list of floats.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("text must not be empty")

    model = _get_model()
    vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vector.tolist()

