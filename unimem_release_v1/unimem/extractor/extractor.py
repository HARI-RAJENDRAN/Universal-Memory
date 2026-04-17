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


class SimpleMemoryExtractor:
    """Basic extractor that treats full text as a single memory."""

    def extract(self, text: str) -> list[dict]:
        """Extract memory from text in a structured format.

        Args:
            text: Raw input text from user or conversation.

        Returns:
            A list containing one memory dictionary with keys:
            - type: Memory type label (currently always "text")
            - content: The normalized memory text
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        normalized = text.strip()
        if not normalized:
            return []

        return [{"type": "text", "content": normalized}]

