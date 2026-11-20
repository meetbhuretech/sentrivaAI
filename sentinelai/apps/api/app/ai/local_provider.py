"""Optional local-model adapter stub.

Without a running local OpenAI-compatible endpoint, this provider reports
unavailable and the orchestrator falls back to deterministic rules.
"""

from __future__ import annotations

import os

from app.ai.openai_provider import OpenAIProvider


class LocalProvider(OpenAIProvider):
    name = "local"

    def __init__(self) -> None:
        # Reuse OpenAI client against a local base URL (e.g. Ollama/vLLM).
        super().__init__()
        self._base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
        self._api_key = os.getenv("LOCAL_LLM_API_KEY", "local")

    async def is_available(self) -> bool:
        # Only claim available if explicitly enabled — avoids false LLM use.
        return os.getenv("ENABLE_LOCAL_LLM", "false").lower() in {"1", "true", "yes"}
