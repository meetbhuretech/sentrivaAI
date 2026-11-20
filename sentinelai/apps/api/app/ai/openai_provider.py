from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.ai.base import AIProvider, AIResponse, StructuredRequest, TokenUsage
from app.ai.pricing import estimate_cost_usd
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def complete_structured(self, request: StructuredRequest, *, model: str) -> AIResponse:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package not installed") from exc

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        start = time.perf_counter()
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        # Ask for JSON object; validate against expected keys client-side.
        messages.append(
            {
                "role": "system",
                "content": (
                    f"Respond with a single JSON object matching schema '{request.schema_name}'. "
                    "Do not invent telemetry. Only use provided evidence references."
                ),
            }
        )
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        parsed: dict[str, Any] | None
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        usage = TokenUsage(
            prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(resp.usage, "total_tokens", 0) or 0,
        )
        cost = self.estimate_cost(usage, model)
        return AIResponse(
            content=content,
            parsed=parsed,
            model=model,
            provider=self.name,
            usage=usage,
            latency_ms=(time.perf_counter() - start) * 1000,
            estimated_cost_usd=cost,
            raw={"id": getattr(resp, "id", None)},
        )

    def estimate_cost(self, usage: TokenUsage, model: str) -> float:
        return estimate_cost_usd(model, usage.prompt_tokens, usage.completion_tokens)
