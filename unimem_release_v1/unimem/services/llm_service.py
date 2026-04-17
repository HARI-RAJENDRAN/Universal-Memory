"""LLM service layer for memory-augmented generation."""

from __future__ import annotations

from unimem.llm.local_llm import LLMClient
from unimem.core.logger import get_logger

logger = get_logger(__name__)

class LLMService:
    """Handles context-aware generation, prompt engineering, and failover semantics."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate_contextual_response(
        self, query: str, context_items: list[str]
    ) -> str:
        """Builds a customized prompt with user context and invokes the LLM."""
        prompt = self._build_prompt(query, context_items)

        try:
            reply = self.llm_client.generate(prompt)
        except Exception as exc:
            return self._fallback_response(query, context_items, error=exc)

        # Handle specific string-based errors from LocalLLMClient
        if isinstance(reply, str) and self._is_local_llm_failure_message(reply):
            return self._fallback_response(query, context_items, error=None)

        return reply

    def _build_prompt(self, query: str, context_items: list[str]) -> str:
        """Construct prompt without exposing system 'memory' terminology."""
        if context_items:
            context_block = "\n".join(f"- {item}" for item in context_items)
            personalized_section = (
                "Personalized context regarding the user:\n"
                f"{context_block}\n\n"
            )
        else:
            personalized_section = ""

        return (
            "You are a helpful and intelligent AI assistant.\n"
            f"{personalized_section}"
            "Answer the user naturally. Use the personalized context if it relates to "
            "the user's query, but avoid explicitly stating 'based on what you told me'.\n\n"
            f"User: {query}\n\n"
            "Assistant:"
        )

    @staticmethod
    def _is_local_llm_failure_message(text: str) -> bool:
        markers = (
            "Ollama is unavailable.",
            "Local LLM request timed out",
            "Received an invalid response from Ollama.",
            "Local LLM request failed:",
            "Ollama returned an unexpected response format.",
        )
        return any(text.startswith(m) for m in markers)

    def _fallback_response(
        self,
        query: str,
        context_items: list[str],
        error: BaseException | None = None,
    ) -> str:
        """Provides graceful fallback to raw semantic retrieval if generation engine fails."""
        if error:
            logger.warning("LLM generation failed explicitly: %s", error)
        else:
            logger.warning("LLM generation failed (internal string marker detected).")

        if not context_items:
            return (
                "The AI generation engine is currently unreachable, and I have no "
                "relevant context to augment this query. Please try again later."
            )
            
        logger.info("Failing over to raw semantic retrieval results.")
        context_str = '; '.join(context_items)
        return (
            "[SYSTEM: Generation Engine Offline — Falling back to semantic retrieval]\n"
            f"Top context regarding your query: {context_str}"
        )
