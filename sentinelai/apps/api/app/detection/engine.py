"""Detection engine: gather telemetry → rules + anomaly → alerts → incidents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sentinelai_contracts import Severity
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.detection.anomaly import AnomalyScore, score_against_baseline
from app.detection.lifecycle import (
    get_or_create_open_incident,
    incident_title_for,
    max_severity,
    maybe_resolve_incidents,
    resolve_recovered_alerts,
    upsert_alert,
)
from app.detection.rules import (
    CandidateAlert,
    DetectionThresholds,
    rule_cpu_saturation,
    rule_db_pool_saturation,
    rule_dependency_timeouts,
    rule_error_rate,
    rule_health_check_failed,
    rule_latency_p95,
    rule_memory_pressure,
    rule_redis_connection_errors,
)
from app.models.service import Service
from app.models.telemetry import MetricSample, TelemetryLog

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    evaluated_at: datetime
    services_checked: int
    candidates: list[CandidateAlert] = field(default_factory=list)
    anomaly_scores: list[AnomalyScore] = field(default_factory=list)
    alerts_created: int = 0
    alerts_updated: int = 0
    alerts_resolved: int = 0
    incidents_created: int = 0
    incidents_updated: int = 0
    incidents_resolved: int = 0
    incident_ids: list[str] = field(default_factory=list)


class DetectionEngine:
    def __init__(
        self,
        thresholds: DetectionThresholds | None = None,
        *,
        lookback_minutes: int = 15,
        baseline_minutes: int = 60,
    ) -> None:
        self.thresholds = thresholds or DetectionThresholds()
        self.lookback_minutes = lookback_minutes
        self.baseline_minutes = baseline_minutes

    async def run(self, db: AsyncSession) -> DetectionResult:
        now = datetime.now(UTC)
        result = DetectionResult(evaluated_at=now, services_checked=0)
        window_start = now - timedelta(minutes=self.lookback_minutes)
        baseline_start = now - timedelta(minutes=self.baseline_minutes)

        services = list(
            (await db.execute(select(Service).where(Service.base_url.is_not(None))))
            .scalars()
            .all()
        )
        result.services_checked = len(services)
        candidates: list[CandidateAlert] = []

        for svc in services:
            name = svc.name
            latest = await self._latest_metrics(db, name, window_start)
            health_alert = rule_health_check_failed(name, svc.status.value)
            if health_alert:
                candidates.append(health_alert)

            if "http_error_rate" in latest:
                alert = rule_error_rate(name, latest["http_error_rate"], self.thresholds)
                if alert:
                    candidates.append(alert)
            if "http_latency_p95_ms" in latest:
                alert = rule_latency_p95(name, latest["http_latency_p95_ms"], self.thresholds)
                if alert:
                    candidates.append(alert)
            if "memory_percent" in latest:
                alert = rule_memory_pressure(name, latest["memory_percent"], self.thresholds)
                if alert:
                    candidates.append(alert)
            if "cpu_percent" in latest:
                alert = rule_cpu_saturation(name, latest["cpu_percent"], self.thresholds)
                if alert:
                    candidates.append(alert)
            if "db_pool_usage_ratio" in latest:
                alert = rule_db_pool_saturation(
                    name, latest["db_pool_usage_ratio"], self.thresholds
                )
                if alert:
                    candidates.append(alert)

            timeout_count = await self._count_logs(
                db,
                name,
                window_start,
                patterns=["timeout", "timed out", "dependency timeout"],
            )
            timeout_alert = rule_dependency_timeouts(name, timeout_count, self.thresholds)
            if timeout_alert:
                candidates.append(timeout_alert)

            redis_count = await self._count_logs(
                db,
                name,
                window_start,
                patterns=["redis connection", "redis unavailable", "connection refused"],
            )
            redis_alert = rule_redis_connection_errors(name, redis_count)
            if redis_alert:
                candidates.append(redis_alert)

            # Anomaly scoring on error rate and latency (explainable z-score)
            for metric in ("http_error_rate", "http_latency_p95_ms"):
                if metric not in latest:
                    continue
                baseline = await self._baseline_values(
                    db, name, metric, baseline_start, window_start
                )
                score = score_against_baseline(
                    metric_name=metric,
                    service_name=name,
                    current_value=latest[metric],
                    baseline_values=baseline,
                )
                result.anomaly_scores.append(score)
                if score.is_anomalous:
                    sev = Severity.HIGH if score.severity_hint == "high" else Severity.MEDIUM
                    candidates.append(
                        CandidateAlert(
                            rule_id=f"anomaly_{metric}",
                            service_name=name,
                            severity=sev,
                            title=f"Anomalous {metric} on {name}",
                            description=score.explanation,
                            fingerprint=f"anomaly_{metric}:{name}",
                            labels={
                                "metric": metric,
                                "value": score.value,
                                "z_score": score.z_score,
                                "baseline_mean": score.baseline_mean,
                                "baseline_std": score.baseline_std,
                            },
                            annotations={
                                "method": "z_score",
                                "sample_count": score.sample_count,
                            },
                        )
                    )

        result.candidates = candidates
        firing_fps = {c.fingerprint for c in candidates}

        # Group by service and upsert into incidents
        by_service: dict[str, list[CandidateAlert]] = {}
        for c in candidates:
            by_service.setdefault(c.service_name, []).append(c)

        # Also merge multi-service candidates into shared incidents when overlapping
        # open incidents already exist (handled in get_or_create_open_incident).
        for service_name, group in by_service.items():
            severity = max_severity(c.severity for c in group)
            title = incident_title_for(group)
            summary = "; ".join(c.description for c in group[:5])
            incident, created = await get_or_create_open_incident(
                db,
                service_names=[service_name],
                severity=severity,
                title=title,
                summary=summary,
            )
            if created:
                result.incidents_created += 1
            else:
                result.incidents_updated += 1
            result.incident_ids.append(str(incident.id))

            for candidate in group:
                _, was_created = await upsert_alert(db, candidate, incident_id=incident.id)
                if was_created:
                    result.alerts_created += 1
                else:
                    result.alerts_updated += 1

        resolved_alerts = await resolve_recovered_alerts(
            db, still_firing_fingerprints=firing_fps
        )
        result.alerts_resolved = len(resolved_alerts)
        resolved_incidents = await maybe_resolve_incidents(db)
        result.incidents_resolved = len(resolved_incidents)

        logger.info(
            "detection cycle complete services=%s candidates=%s alerts_created=%s incidents_created=%s",
            result.services_checked,
            len(candidates),
            result.alerts_created,
            result.incidents_created,
        )
        return result

    async def _latest_metrics(
        self, db: AsyncSession, service_name: str, since: datetime
    ) -> dict[str, float]:
        """Latest sample per metric in the lookback window (spike-sensitive)."""
        # Distinct metric names first, then fetch newest row for each.
        names = (
            await db.execute(
                select(MetricSample.metric_name)
                .where(MetricSample.service_name == service_name)
                .where(MetricSample.timestamp >= since)
                .distinct()
            )
        ).scalars().all()
        latest: dict[str, float] = {}
        for metric_name in names:
            row = (
                await db.execute(
                    select(MetricSample.value)
                    .where(MetricSample.service_name == service_name)
                    .where(MetricSample.metric_name == metric_name)
                    .where(MetricSample.timestamp >= since)
                    .order_by(MetricSample.timestamp.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row is not None:
                latest[metric_name] = float(row)
        return latest

    async def _baseline_values(
        self,
        db: AsyncSession,
        service_name: str,
        metric_name: str,
        baseline_start: datetime,
        baseline_end: datetime,
    ) -> list[float]:
        rows = (
            await db.execute(
                select(MetricSample.value)
                .where(MetricSample.service_name == service_name)
                .where(MetricSample.metric_name == metric_name)
                .where(MetricSample.timestamp >= baseline_start)
                .where(MetricSample.timestamp < baseline_end)
                .order_by(MetricSample.timestamp)
            )
        ).scalars().all()
        return [float(v) for v in rows]

    async def _count_logs(
        self,
        db: AsyncSession,
        service_name: str,
        since: datetime,
        patterns: list[str],
    ) -> int:
        clauses = [TelemetryLog.message.ilike(f"%{p}%") for p in patterns]
        q: Select[Any] = (
            select(func.count())
            .select_from(TelemetryLog)
            .where(TelemetryLog.service_name == service_name)
            .where(TelemetryLog.timestamp >= since)
            .where(TelemetryLog.level.in_(["ERROR", "WARN", "WARNING"]))
            .where(or_(*clauses))
        )
        return int(await db.scalar(q) or 0)
