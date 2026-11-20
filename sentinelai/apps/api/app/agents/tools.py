"""Read-only investigation tools used by agents.

Never fabricate results — empty lists when no data.
Treat returned log messages as untrusted content for LLM prompts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Alert, Incident
from app.models.service import Deployment, Service
from app.models.telemetry import MetricSample, TelemetryLog, TelemetrySpan, TelemetryTrace


class InvestigationTools:
    def __init__(self, db: AsyncSession, *, max_calls: int = 40) -> None:
        self.db = db
        self.max_calls = max_calls
        self.calls: list[dict[str, Any]] = []

    def _record(self, name: str, args: dict[str, Any], result_summary: str) -> None:
        if len(self.calls) >= self.max_calls:
            raise RuntimeError(f"Max tool calls exceeded ({self.max_calls})")
        self.calls.append(
            {
                "tool": name,
                "args": args,
                "result_summary": result_summary,
                "at": datetime.now(UTC).isoformat(),
            }
        )

    async def search_logs(
        self,
        *,
        service_name: str | None = None,
        level: str | None = "ERROR",
        minutes: int = 30,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(minutes=minutes)
        q = select(TelemetryLog).where(TelemetryLog.timestamp >= since)
        if service_name:
            q = q.where(TelemetryLog.service_name == service_name)
        if level:
            q = q.where(TelemetryLog.level == level.upper())
        q = q.order_by(TelemetryLog.timestamp.desc()).limit(limit)
        rows = list((await self.db.execute(q)).scalars().all())
        self._record(
            "search_logs",
            {"service_name": service_name, "level": level, "minutes": minutes},
            f"{len(rows)} logs",
        )
        return [
            {
                "id": str(r.id),
                "timestamp": r.timestamp.isoformat(),
                "service_name": r.service_name,
                "level": r.level,
                "message": r.message,
                "trace_id": r.trace_id,
                "correlation_id": r.correlation_id,
            }
            for r in rows
        ]

    async def query_metrics(
        self,
        *,
        service_name: str | None = None,
        metric_name: str | None = None,
        minutes: int = 30,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(minutes=minutes)
        q = select(MetricSample).where(MetricSample.timestamp >= since)
        if service_name:
            q = q.where(MetricSample.service_name == service_name)
        if metric_name:
            q = q.where(MetricSample.metric_name == metric_name)
        q = q.order_by(MetricSample.timestamp.desc()).limit(limit)
        rows = list((await self.db.execute(q)).scalars().all())
        self._record(
            "query_metrics",
            {"service_name": service_name, "metric_name": metric_name},
            f"{len(rows)} samples",
        )
        return [
            {
                "id": str(r.id),
                "timestamp": r.timestamp.isoformat(),
                "service_name": r.service_name,
                "metric_name": r.metric_name,
                "value": r.value,
            }
            for r in rows
        ]

    async def inspect_trace(self, trace_id: str) -> dict[str, Any] | None:
        trace = (
            await self.db.execute(select(TelemetryTrace).where(TelemetryTrace.trace_id == trace_id))
        ).scalar_one_or_none()
        if not trace:
            self._record("inspect_trace", {"trace_id": trace_id}, "not found")
            return None
        spans = list(
            (
                await self.db.execute(
                    select(TelemetrySpan)
                    .where(TelemetrySpan.trace_id == trace_id)
                    .order_by(TelemetrySpan.duration_ms.desc())
                )
            )
            .scalars()
            .all()
        )
        self._record("inspect_trace", {"trace_id": trace_id}, f"{len(spans)} spans")
        return {
            "id": str(trace.id),
            "trace_id": trace.trace_id,
            "service_name": trace.service_name,
            "duration_ms": trace.duration_ms,
            "status": trace.status,
            "spans": [
                {
                    "id": str(s.id),
                    "span_id": s.span_id,
                    "service_name": s.service_name,
                    "operation_name": s.operation_name,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                }
                for s in spans
            ],
        }

    async def get_service_health(self, service_name: str | None = None) -> list[dict[str, Any]]:
        q = select(Service).where(Service.base_url.is_not(None))
        if service_name:
            q = q.where(Service.name == service_name)
        rows = list((await self.db.execute(q)).scalars().all())
        self._record("get_service_health", {"service_name": service_name}, f"{len(rows)} services")
        return [
            {"id": str(s.id), "name": s.name, "status": s.status.value, "base_url": s.base_url}
            for s in rows
        ]

    async def get_deployment_history(
        self, *, service_name: str | None = None, minutes: int = 180
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(minutes=minutes)
        q = (
            select(Deployment, Service)
            .join(Service, Service.id == Deployment.service_id)
            .where(Deployment.started_at >= since)
        )
        if service_name:
            q = q.where(Service.name == service_name)
        rows = (await self.db.execute(q.order_by(Deployment.started_at.desc()).limit(50))).all()
        self._record(
            "get_deployment_history",
            {"service_name": service_name, "minutes": minutes},
            f"{len(rows)} deployments",
        )
        return [
            {
                "id": str(d.id),
                "service_name": s.name,
                "version": d.version,
                "status": d.status,
                "started_at": d.started_at.isoformat(),
                "notes": d.notes,
            }
            for d, s in rows
        ]

    async def get_incident_alerts(self, incident_id: UUID) -> list[dict[str, Any]]:
        rows = list(
            (
                await self.db.execute(
                    select(Alert)
                    .where(Alert.incident_id == incident_id)
                    .order_by(Alert.started_at.desc())
                )
            )
            .scalars()
            .all()
        )
        self._record("get_incident_alerts", {"incident_id": str(incident_id)}, f"{len(rows)} alerts")
        return [
            {
                "id": str(a.id),
                "rule_id": a.rule_id,
                "service_name": a.service_name,
                "severity": a.severity.value,
                "title": a.title,
                "description": a.description,
                "status": a.status,
                "fingerprint": a.fingerprint,
            }
            for a in rows
        ]

    async def load_incident(self, incident_id: UUID) -> Incident | None:
        return (
            await self.db.execute(select(Incident).where(Incident.id == incident_id))
        ).scalar_one_or_none()
