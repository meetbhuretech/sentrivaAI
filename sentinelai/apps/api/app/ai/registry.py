from __future__ import annotations

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base import AIProvider
from app.ai.deterministic import DeterministicProvider
from app.ai.local_provider import LocalProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.config import get_settings


def get_provider(name: str | None = None) -> AIProvider:
    settings = get_settings()
    key = (name or settings.default_ai_provider or "deterministic").lower()
    providers: dict[str, AIProvider] = {
        "deterministic": DeterministicProvider(),
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "local": LocalProvider(),
    }
    return providers.get(key, providers["deterministic"])


async def resolve_provider(name: str | None = None) -> tuple[AIProvider, str]:
    """Return (provider, effective_name). Falls back to deterministic if unavailable."""
    primary = get_provider(name)
    if await primary.is_available():
        return primary, primary.name
    return DeterministicProvider(), "deterministic"
