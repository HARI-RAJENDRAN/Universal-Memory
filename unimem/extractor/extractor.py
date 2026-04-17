"""Memory extraction module.

Current behavior is intentionally simple:
- Accept raw text input
- Return one structured memory item

The design is extendable so future versions can plug in an LLM-based extractor
without changing callers.
"""

from __future__ import annotations

from typing import Protocol


class Extractor(Protocol):
    """Protocol for extraction implementations."""

    def extract(self, text: str) -> list[dict]:
        """Extract structured memory items from input text."""


def is_suspicious(text: str) -> bool:
    """Security heuristic engine blocking prompt injection attacks."""
    t = text.lower()
    malicious = ["ignore previous", "always say", "you must", "disregard", "jailbreak"]
    return any(p in t for p in malicious)

def detect_context(text: str) -> str:
    """Classifies memory domain rules to isolate SQL groupings."""
    t = text.lower()
    
    if "pizza" in t or "pepperoni" in t or "mushrooms on pizza" in t:
        return "food:pizza"
    if "soup" in t or "broth" in t or "mushroom soup" in t:
        return "food:soup"
    if "python" in t or "programming" in t or "code" in t or "language" in t:
        return "programming"
        
    return "general"

class SimpleMemoryExtractor:
    """Basic extractor that treats full text as a single memory."""

    def extract(self, text: str) -> list[dict]:
        """Extract memory from text in a structured format."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        normalized = text.strip()
        if not normalized:
            return []
            
        ctx = detect_context(normalized)

        return [{"type": "text", "content": normalized, "context": ctx}]

