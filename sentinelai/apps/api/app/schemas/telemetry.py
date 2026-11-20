from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class LogIngestItem(APIModel):
    timestamp: datetime
    service_name: str
    level: str
    message: str
    environment: str = "local"
    trace_id: str | None = None
    span_id: str | None = None
    correlation_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class LogIngestRequest(APIModel):
    logs: list[LogIngestItem] = Field(min_length=1, max_length=1000)


class MetricIngestItem(APIModel):
    timestamp: datetime
    service_name: str
    metric_name: str
    value: float
    labels: dict[str, Any] = Field(default_factory=dict)


class MetricIngestRequest(APIModel):
    metrics: list[MetricIngestItem] = Field(min_length=1, max_length=1000)


class SpanIngestItem(APIModel):
    span_id: str
    parent_span_id: str | None = None
    service_name: str
    operation_name: str
    started_at: datetime
    duration_ms: float
    status: str = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceIngestItem(APIModel):
    trace_id: str
    service_name: str
    root_operation: str | None = None
    started_at: datetime
    duration_ms: float | None = None
    status: str = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)
    spans: list[SpanIngestItem] = Field(default_factory=list)


class TraceIngestRequest(APIModel):
    traces: list[TraceIngestItem] = Field(min_length=1, max_length=200)


class DeploymentIngestItem(APIModel):
    service_name: str
    version: str
    commit_sha: str | None = None
    status: str = "success"
    started_at: datetime
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class DeploymentIngestRequest(APIModel):
    deployments: list[DeploymentIngestItem] = Field(min_length=1, max_length=100)


class IngestAccepted(APIModel):
    accepted: int
    status: str = "accepted"


class LogOut(APIModel):
    id: UUID
    timestamp: datetime
    service_name: str
    level: str
    message: str
    trace_id: str | None = None
    correlation_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class MetricOut(APIModel):
    id: UUID
    timestamp: datetime
    service_name: str
    metric_name: str
    value: float
    labels: dict[str, Any] = Field(default_factory=dict)


class TraceOut(APIModel):
    id: UUID
    trace_id: str
    service_name: str
    root_operation: str | None = None
    started_at: datetime
    duration_ms: float | None = None
    status: str


class SpanOut(APIModel):
    id: UUID
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    service_name: str
    operation_name: str
    started_at: datetime
    duration_ms: float
    status: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceDetail(TraceOut):
    spans: list[SpanOut] = Field(default_factory=list)
