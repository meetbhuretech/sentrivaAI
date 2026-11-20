from datetime import datetime
from uuid import UUID

from sentinelai_contracts import IncidentStatus, Severity

from app.schemas.common import APIModel


class IncidentOut(APIModel):
    id: UUID
    title: str
    status: IncidentStatus
    severity: Severity
    service_names: list[str]
    started_at: datetime | None = None
    detected_at: datetime
    resolved_at: datetime | None = None
    mttr_seconds: int | None = None
    summary: str | None = None


class IncidentUpdate(APIModel):
    status: IncidentStatus | None = None
    summary: str | None = None
