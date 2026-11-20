from datetime import datetime
from typing import Any
from uuid import UUID

from sentinelai_contracts import InvestigationStatus

from app.schemas.common import APIModel


class StartInvestigationRequest(APIModel):
    provider: str | None = None
    model: str | None = None


class InvestigationOut(APIModel):
    id: UUID
    incident_id: UUID
    status: InvestigationStatus
    current_step: str
    provider: str
    model: str
    prompt_version: str
    rca: dict[str, Any] | None = None
    token_usage: dict[str, Any] = {}
    estimated_cost_usd: float = 0.0
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class InvestigationEvidenceOut(APIModel):
    findings: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
