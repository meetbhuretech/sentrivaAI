from datetime import UTC, datetime, timedelta

from sentinelai_contracts import IncidentStatus, InvestigationStatus, ServiceStatus, Severity
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.service import Service
from app.models.telemetry import MetricSample
from app.schemas.overview import (
    AIInvestigationStats,
    LatencyStats,
    OverviewResponse,
    ResourceUtilization,
)


async def build_overview(
    db: AsyncSession,
    *,
    service_name: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> OverviewResponse:
    """Compute overview from persisted data only — never hardcoded live metrics."""
    to_ts = to_ts or datetime.now(UTC)
    from_ts = from_ts or (to_ts - timedelta(hours=1))

    services = list(
        (await db.execute(select(Service).where(Service.base_url.is_not(None)))).scalars().all()
    )

    total_services = len(services)
    healthy_services = sum(1 for s in services if s.status == ServiceStatus.HEALTHY)

    active_statuses = [
        IncidentStatus.OPEN,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.MITIGATING,
    ]
    incidents_q = select(Incident).where(Incident.status.in_(active_statuses))
    if service_name:
        incidents_q = incidents_q.where(Incident.service_names.any(service_name))
    incidents = (await db.execute(incidents_q)).scalars().all()

    severity_distribution = {s.value: 0 for s in Severity}
    for inc in incidents:
        severity_distribution[inc.severity.value] += 1

    # Metrics from samples in window (0 if none yet — honest empty state)
    async def latest_avg(metric: str) -> float:
        q = (
            select(func.avg(MetricSample.value))
            .where(MetricSample.metric_name == metric)
            .where(MetricSample.timestamp >= from_ts)
            .where(MetricSample.timestamp <= to_ts)
        )
        if service_name:
            q = q.where(MetricSample.service_name == service_name)
        val = await db.scalar(q)
        return float(val) if val is not None else 0.0

    request_rate = await latest_avg("http_requests_per_second")
    error_rate = await latest_avg("http_error_rate")
    p50 = await latest_avg("http_latency_p50_ms")
    p95 = await latest_avg("http_latency_p95_ms")
    p99 = await latest_avg("http_latency_p99_ms")
    cpu = await latest_avg("cpu_percent")
    mem = await latest_avg("memory_percent")

    mttr = await db.scalar(
        select(func.avg(Incident.mttr_seconds)).where(Incident.mttr_seconds.is_not(None))
    )

    active_inv = await db.scalar(
        select(func.count())
        .select_from(Investigation)
        .where(
            Investigation.status.notin_(
                [
                    InvestigationStatus.COMPLETED,
                    InvestigationStatus.FAILED,
                    InvestigationStatus.CANCELLED,
                    InvestigationStatus.TIMED_OUT,
                ]
            )
        )
    )
    completed_inv = await db.scalar(
        select(func.count())
        .select_from(Investigation)
        .where(Investigation.status == InvestigationStatus.COMPLETED)
    )
    failed_inv = await db.scalar(
        select(func.count())
        .select_from(Investigation)
        .where(
            Investigation.status.in_(
                [InvestigationStatus.FAILED, InvestigationStatus.TIMED_OUT]
            )
        )
    )

    return OverviewResponse(
        total_services=total_services,
        healthy_services=healthy_services,
        active_incidents=len(incidents),
        severity_distribution=severity_distribution,
        request_rate=request_rate,
        error_rate=error_rate,
        latency=LatencyStats(p50_ms=p50, p95_ms=p95, p99_ms=p99),
        resource_utilization=ResourceUtilization(cpu_percent=cpu, memory_percent=mem),
        mttr_seconds=float(mttr) if mttr is not None else None,
        ai_investigations=AIInvestigationStats(
            active=int(active_inv or 0),
            completed=int(completed_inv or 0),
            failed=int(failed_inv or 0),
        ),
        generated_at=datetime.now(UTC),
    )
