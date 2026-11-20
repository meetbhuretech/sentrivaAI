from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, verify_simulator_token
from app.core.errors import AppError
from app.schemas.common import Page
from app.schemas.telemetry import (
    DeploymentIngestRequest,
    IngestAccepted,
    LogIngestRequest,
    LogOut,
    MetricIngestRequest,
    MetricOut,
    TraceDetail,
    TraceIngestRequest,
    TraceOut,
)
from app.services import telemetry as telemetry_service

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
SimulatorAuth = Annotated[None, Depends(verify_simulator_token)]


@router.post("/logs", response_model=IngestAccepted, status_code=202)
async def ingest_logs(
    body: LogIngestRequest,
    db: DbSession,
    _: SimulatorAuth,
) -> IngestAccepted:
    accepted = await telemetry_service.ingest_logs(db, body)
    return IngestAccepted(accepted=accepted)


@router.post("/metrics", response_model=IngestAccepted, status_code=202)
async def ingest_metrics(
    body: MetricIngestRequest,
    db: DbSession,
    _: SimulatorAuth,
) -> IngestAccepted:
    accepted = await telemetry_service.ingest_metrics(db, body)
    return IngestAccepted(accepted=accepted)


@router.post("/traces", response_model=IngestAccepted, status_code=202)
async def ingest_traces(
    body: TraceIngestRequest,
    db: DbSession,
    _: SimulatorAuth,
) -> IngestAccepted:
    accepted = await telemetry_service.ingest_traces(db, body)
    return IngestAccepted(accepted=accepted)


@router.post("/deployments", response_model=IngestAccepted, status_code=202)
async def ingest_deployments(
    body: DeploymentIngestRequest,
    db: DbSession,
    _: SimulatorAuth,
) -> IngestAccepted:
    accepted = await telemetry_service.ingest_deployments(db, body)
    return IngestAccepted(accepted=accepted)


@router.get("/logs", response_model=Page[LogOut])
async def search_logs(
    db: DbSession,
    _user: CurrentUser,
    service: str | None = None,
    level: str | None = None,
    q: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[LogOut]:
    items, total = await telemetry_service.search_logs(
        db,
        service=service,
        level=level,
        q=q,
        trace_id=trace_id,
        correlation_id=correlation_id,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/metrics", response_model=Page[MetricOut])
async def query_metrics(
    db: DbSession,
    _user: CurrentUser,
    service: str | None = None,
    metric_name: str | None = None,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[MetricOut]:
    items, total = await telemetry_service.query_metrics(
        db,
        service=service,
        metric_name=metric_name,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/traces", response_model=Page[TraceOut])
async def list_traces(
    db: DbSession,
    _user: CurrentUser,
    service: str | None = None,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[TraceOut]:
    items, total = await telemetry_service.list_traces(
        db,
        service=service,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/traces/{trace_id}", response_model=TraceDetail)
async def get_trace(trace_id: str, db: DbSession, _user: CurrentUser) -> TraceDetail:
    result = await telemetry_service.get_trace_detail(db, trace_id)
    if result is None:
        raise AppError("NOT_FOUND", "Trace not found", status_code=404)
    trace, spans = result
    return TraceDetail(
        id=trace.id,
        trace_id=trace.trace_id,
        service_name=trace.service_name,
        root_operation=trace.root_operation,
        started_at=trace.started_at,
        duration_ms=trace.duration_ms,
        status=trace.status,
        spans=spans,
    )
