from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import redact_secrets
from app.models.service import Deployment, Service
from app.models.telemetry import MetricSample, TelemetryLog, TelemetrySpan, TelemetryTrace
from app.schemas.telemetry import (
    DeploymentIngestRequest,
    LogIngestRequest,
    MetricIngestRequest,
    TraceIngestRequest,
)


def _safe_message(message: str) -> str:
    return redact_secrets(message)


async def ingest_logs(db: AsyncSession, body: LogIngestRequest) -> int:
    rows = [
        TelemetryLog(
            timestamp=item.timestamp,
            service_name=item.service_name,
            environment=item.environment,
            level=item.level.upper(),
            message=_safe_message(item.message),
            trace_id=item.trace_id,
            span_id=item.span_id,
            correlation_id=item.correlation_id,
            attributes=item.attributes,
            raw=item.model_dump(mode="json"),
        )
        for item in body.logs
    ]
    db.add_all(rows)
    await db.flush()
    return len(rows)


async def ingest_metrics(db: AsyncSession, body: MetricIngestRequest) -> int:
    rows = [
        MetricSample(
            timestamp=item.timestamp,
            service_name=item.service_name,
            metric_name=item.metric_name,
            value=item.value,
            labels=item.labels,
        )
        for item in body.metrics
    ]
    db.add_all(rows)
    await db.flush()
    return len(rows)


async def ingest_traces(db: AsyncSession, body: TraceIngestRequest) -> int:
    count = 0
    for item in body.traces:
        existing = (
            await db.execute(select(TelemetryTrace).where(TelemetryTrace.trace_id == item.trace_id))
        ).scalar_one_or_none()
        if existing:
            trace = existing
            trace.duration_ms = item.duration_ms
            trace.status = item.status
        else:
            trace = TelemetryTrace(
                trace_id=item.trace_id,
                service_name=item.service_name,
                root_operation=item.root_operation,
                started_at=item.started_at,
                duration_ms=item.duration_ms,
                status=item.status,
                attributes=item.attributes,
            )
            db.add(trace)
            await db.flush()
        for span in item.spans:
            db.add(
                TelemetrySpan(
                    trace_pk=trace.id,
                    trace_id=item.trace_id,
                    span_id=span.span_id,
                    parent_span_id=span.parent_span_id,
                    service_name=span.service_name,
                    operation_name=span.operation_name,
                    started_at=span.started_at,
                    duration_ms=span.duration_ms,
                    status=span.status,
                    attributes=span.attributes,
                )
            )
        count += 1
    await db.flush()
    return count


async def ingest_deployments(db: AsyncSession, body: DeploymentIngestRequest) -> int:
    count = 0
    for item in body.deployments:
        svc = (
            await db.execute(select(Service).where(Service.name == item.service_name))
        ).scalar_one_or_none()
        if svc is None:
            continue
        db.add(
            Deployment(
                service_id=svc.id,
                version=item.version,
                commit_sha=item.commit_sha,
                status=item.status,
                started_at=item.started_at,
                completed_at=item.completed_at,
                metadata_json=item.metadata,
                notes=item.notes,
            )
        )
        count += 1
    await db.flush()
    return count


async def search_logs(
    db: AsyncSession,
    *,
    service: str | None,
    level: str | None,
    q: str | None,
    trace_id: str | None,
    correlation_id: str | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[TelemetryLog], int]:
    filters = []
    if service:
        filters.append(TelemetryLog.service_name == service)
    if level:
        filters.append(TelemetryLog.level == level.upper())
    if q:
        filters.append(TelemetryLog.message.ilike(f"%{q}%"))
    if trace_id:
        filters.append(TelemetryLog.trace_id == trace_id)
    if correlation_id:
        filters.append(TelemetryLog.correlation_id == correlation_id)
    if from_ts:
        filters.append(TelemetryLog.timestamp >= from_ts)
    if to_ts:
        filters.append(TelemetryLog.timestamp <= to_ts)

    count_q = select(func.count()).select_from(TelemetryLog)
    data_q = select(TelemetryLog)
    for f in filters:
        count_q = count_q.where(f)
        data_q = data_q.where(f)
    total = await db.scalar(count_q) or 0
    data_q = (
        data_q.order_by(TelemetryLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(data_q)).scalars().all())
    return items, total


async def query_metrics(
    db: AsyncSession,
    *,
    service: str | None,
    metric_name: str | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[MetricSample], int]:
    filters = []
    if service:
        filters.append(MetricSample.service_name == service)
    if metric_name:
        filters.append(MetricSample.metric_name == metric_name)
    if from_ts:
        filters.append(MetricSample.timestamp >= from_ts)
    if to_ts:
        filters.append(MetricSample.timestamp <= to_ts)
    count_q = select(func.count()).select_from(MetricSample)
    data_q = select(MetricSample)
    for f in filters:
        count_q = count_q.where(f)
        data_q = data_q.where(f)
    total = await db.scalar(count_q) or 0
    data_q = (
        data_q.order_by(MetricSample.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list((await db.execute(data_q)).scalars().all()), total


async def list_traces(
    db: AsyncSession,
    *,
    service: str | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[TelemetryTrace], int]:
    filters = []
    if service:
        filters.append(TelemetryTrace.service_name == service)
    if from_ts:
        filters.append(TelemetryTrace.started_at >= from_ts)
    if to_ts:
        filters.append(TelemetryTrace.started_at <= to_ts)
    count_q = select(func.count()).select_from(TelemetryTrace)
    data_q = select(TelemetryTrace)
    for f in filters:
        count_q = count_q.where(f)
        data_q = data_q.where(f)
    total = await db.scalar(count_q) or 0
    data_q = (
        data_q.order_by(TelemetryTrace.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list((await db.execute(data_q)).scalars().all()), total


async def get_trace_detail(
    db: AsyncSession, trace_id: str
) -> tuple[TelemetryTrace, list[TelemetrySpan]] | None:
    trace = (
        await db.execute(select(TelemetryTrace).where(TelemetryTrace.trace_id == trace_id))
    ).scalar_one_or_none()
    if trace is None:
        # also allow lookup by UUID pk
        try:
            pk = UUID(trace_id)
        except ValueError:
            return None
        trace = (await db.execute(select(TelemetryTrace).where(TelemetryTrace.id == pk))).scalar_one_or_none()
        if trace is None:
            return None
    spans = list(
        (
            await db.execute(
                select(TelemetrySpan)
                .where(TelemetrySpan.trace_id == trace.trace_id)
                .order_by(TelemetrySpan.started_at)
            )
        )
        .scalars()
        .all()
    )
    return trace, spans
