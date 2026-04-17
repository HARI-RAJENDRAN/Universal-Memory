"""Local LLM client backed by Ollama REST API."""

from __future__ import annotations

import json
from typing import Protocol
from urllib import error, request


class LLMClient(Protocol):
    """Protocol for pluggable LLM providers."""

    def generate(self, prompt: str) -> str:
        """Generate a text response for the prompt."""


class LocalLLMClient:
    """Ollama-based local LLM client.

    By default this calls the local Ollama service on port 11434 with
    model `llama2`.
    """

    def __init__(
        self,
        model: str = "llama2",
        endpoint: str = "http://localhost:11434/api/generate",
        timeout_seconds: int = 60,
    ) -> None:
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        """Generate a response using Ollama's non-streaming API."""
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            reason = str(getattr(exc, "reason", exc))
            return (
                "Ollama is unavailable. Please make sure Ollama is running "
                "locally and the 'llama2' model is installed. "
                f"Details: {reason}"
            )
        except TimeoutError:
            return "Local LLM request timed out. Please try again."
        except Exception as exc:  # defensive fallback
            return f"Local LLM request failed: {exc}"

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return "Received an invalid response from Ollama."

        answer = parsed.get("response")
        if not isinstance(answer, str):
            return "Ollama returned an unexpected response format."
        return answer.strip()

