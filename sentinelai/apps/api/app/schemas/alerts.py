from datetime import datetime
from typing import Any
from uuid import UUID

from sentinelai_contracts import Severity

from app.schemas.common import APIModel


class AlertOut(APIModel):
    id: UUID
    rule_id: str
    service_name: str
    severity: Severity
    title: str
    description: str
    status: str
    fingerprint: str
    started_at: datetime
    resolved_at: datetime | None = None
    labels: dict[str, Any] = {}
    annotations: dict[str, Any] = {}
    incident_id: UUID | None = None


class AnomalyScoreOut(APIModel):
    metric_name: str
    service_name: str
    value: float
    baseline_mean: float
    baseline_std: float
    sample_count: int
    z_score: float
    is_anomalous: bool
    severity_hint: str
    explanation: str


class DetectionRunResponse(APIModel):
    evaluated_at: datetime
    services_checked: int
    candidates: int
    alerts_created: int
    alerts_updated: int
    alerts_resolved: int
    incidents_created: int
    incidents_updated: int
    incidents_resolved: int
    incident_ids: list[str]
    anomaly_scores: list[AnomalyScoreOut]
