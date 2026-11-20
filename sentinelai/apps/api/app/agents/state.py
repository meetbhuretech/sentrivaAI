from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sentinelai_contracts import InvestigationStatus


class InvestigationStep(StrEnum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    GATHERING_CONTEXT = "gathering_context"
    LOG_INVESTIGATION = "log_investigation"
    METRICS_INVESTIGATION = "metrics_investigation"
    TRACE_INVESTIGATION = "trace_investigation"
    DEPLOYMENT_INVESTIGATION = "deployment_investigation"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    EVIDENCE_EVALUATION = "evidence_evaluation"
    REMEDIATION_PROPOSAL = "remediation_proposal"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class EvidenceRef(BaseModel):
    kind: str
    id: str
    label: str | None = None


class AgentFindingModel(BaseModel):
    agent_name: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    source: str = "deterministic"


class HypothesisModel(BaseModel):
    statement: str
    confidence: float
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    grounded: bool | None = None
    evaluation_notes: str | None = None


class ConfidenceComponents(BaseModel):
    evidence_coverage: float = 0.0
    cross_agent_agreement: float = 0.0
    signal_strength: float = 0.0
    temporal_alignment: float = 0.0


class RootCauseModel(BaseModel):
    summary: str
    probable_root_cause: str
    confidence: float
    confidence_components: ConfidenceComponents
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    alternative_hypotheses: list[HypothesisModel] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    business_impact_estimate: str
    recommended_actions: list[str] = Field(default_factory=list)
    source: str = "deterministic"


class InvestigationState(BaseModel):
    investigation_id: UUID
    incident_id: UUID
    status: InvestigationStatus = InvestigationStatus.PENDING
    current_step: InvestigationStep = InvestigationStep.PENDING
    provider: str = "deterministic"
    model: str = "rules-v1"
    prompt_version: str = "v1"

    context: dict[str, Any] = Field(default_factory=dict)
    log_findings: list[AgentFindingModel] = Field(default_factory=list)
    metrics_findings: list[AgentFindingModel] = Field(default_factory=list)
    trace_findings: list[AgentFindingModel] = Field(default_factory=list)
    deployment_findings: list[AgentFindingModel] = Field(default_factory=list)

    hypotheses: list[HypothesisModel] = Field(default_factory=list)
    evaluated_hypotheses: list[HypothesisModel] = Field(default_factory=list)
    rca: RootCauseModel | None = None
    remediation_plan_id: UUID | None = None

    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    errors: list[str] = Field(default_factory=list)

    started_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    deadline_at: datetime | None = None
    max_tool_calls: int = 40
    tool_calls_used: int = 0
