from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AIMessage(BaseModel):
    role: str  # system | user | assistant
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIResponse(BaseModel):
    content: str
    parsed: dict[str, Any] | None = None
    model: str
    provider: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    raw: dict[str, Any] = Field(default_factory=dict)


class StructuredRequest(BaseModel):
    messages: list[AIMessage]
    schema_name: str
    json_schema: dict[str, Any]
    temperature: float = 0.0
    max_tokens: int = 2000


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def complete_structured(self, request: StructuredRequest, *, model: str) -> AIResponse:
        """Return structured JSON adhering to json_schema when possible."""

    @abstractmethod
    def estimate_cost(self, usage: TokenUsage, model: str) -> float:
        """Estimate USD cost from token usage. Documented rates; not a billing guarantee."""

    async def is_available(self) -> bool:
        return True
