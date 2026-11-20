from datetime import datetime

from app.schemas.common import APIModel


class LatencyStats(APIModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float


class ResourceUtilization(APIModel):
    cpu_percent: float
    memory_percent: float


class AIInvestigationStats(APIModel):
    active: int
    completed: int
    failed: int


class OverviewResponse(APIModel):
    total_services: int
    healthy_services: int
    active_incidents: int
    severity_distribution: dict[str, int]
    request_rate: float
    error_rate: float
    latency: LatencyStats
    resource_utilization: ResourceUtilization
    mttr_seconds: float | None
    ai_investigations: AIInvestigationStats
    generated_at: datetime
