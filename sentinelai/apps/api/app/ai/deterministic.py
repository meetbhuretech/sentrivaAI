"""Deterministic provider — never calls an LLM. Used as default/fallback."""

from __future__ import annotations

import json
import time
from typing import Any

from app.ai.base import AIProvider, AIResponse, StructuredRequest, TokenUsage
from app.ai.pricing import estimate_cost_usd


class DeterministicProvider(AIProvider):
    name = "deterministic"

    async def complete_structured(self, request: StructuredRequest, *, model: str) -> AIResponse:
        start = time.perf_counter()
        # Parse last user message as JSON context if possible; otherwise empty.
        context: dict[str, Any] = {}
        for msg in reversed(request.messages):
            if msg.role == "user":
                try:
                    context = json.loads(msg.content)
                except json.JSONDecodeError:
                    context = {"raw": msg.content}
                break

        parsed = _deterministic_structured(request.schema_name, context)
        content = json.dumps(parsed)
        usage = TokenUsage(
            prompt_tokens=max(1, len(request.messages[-1].content) // 4),
            completion_tokens=max(1, len(content) // 4),
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return AIResponse(
            content=content,
            parsed=parsed,
            model=model or "rules-v1",
            provider=self.name,
            usage=usage,
            latency_ms=(time.perf_counter() - start) * 1000,
            estimated_cost_usd=0.0,
            raw={"source": "deterministic"},
        )

    def estimate_cost(self, usage: TokenUsage, model: str) -> float:
        return estimate_cost_usd(model, usage.prompt_tokens, usage.completion_tokens)

    async def is_available(self) -> bool:
        return True


def _deterministic_structured(schema_name: str, context: dict[str, Any]) -> dict[str, Any]:
    if schema_name == "agent_finding":
        evidence = context.get("evidence_refs") or context.get("evidence") or []
        return {
            "summary": context.get("summary")
            or f"Deterministic analysis for {context.get('agent', 'agent')}",
            "details": context.get("details") or context,
            "evidence_refs": evidence,
            "source": "deterministic",
        }
    if schema_name == "hypotheses":
        return {
            "hypotheses": context.get("hypotheses")
            or [
                {
                    "statement": context.get("probable_cause")
                    or "Insufficient signal for a strong hypothesis",
                    "confidence": float(context.get("confidence", 0.4)),
                    "evidence_refs": context.get("evidence_refs") or [],
                }
            ]
        }
    if schema_name == "root_cause_analysis":
        return context.get("rca") or {
            "summary": context.get("summary") or "Deterministic RCA fallback",
            "probable_root_cause": context.get("probable_root_cause")
            or "Correlated telemetry anomalies",
            "confidence": float(context.get("confidence", 0.4)),
            "confidence_components": context.get("confidence_components") or {},
            "supporting_evidence": context.get("supporting_evidence") or [],
            "alternative_hypotheses": context.get("alternative_hypotheses") or [],
            "affected_services": context.get("affected_services") or [],
            "business_impact_estimate": (
                "[ESTIMATE] Potential user-facing degradation; not measured revenue impact."
            ),
            "recommended_actions": context.get("recommended_actions")
            or ["Review firing alerts", "Inspect recent deployments"],
            "source": "deterministic",
        }
    if schema_name == "remediation_plan":
        return context.get("plan") or {
            "problem_summary": context.get("problem_summary") or "See RCA",
            "rationale": "Deterministic allowlisted remediation suggestion",
            "actions": context.get("actions") or [],
            "risks": "Sandbox-only; may not fully restore service",
            "rollback_steps": ["Re-enable prior scenario state", "Re-run detection"],
            "expected_impact": "[ESTIMATE] May reduce error rate if root cause matches action",
        }
    return {"result": context, "source": "deterministic"}
