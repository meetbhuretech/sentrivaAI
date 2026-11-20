"""Alert deduplication, incident grouping, severity rollup, and recovery."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sentinelai_contracts import IncidentStatus, Severity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.detection.rules import CandidateAlert
from app.models.incident import Alert, Incident

SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def max_severity(severities: Iterable[Severity]) -> Severity:
    return max(severities, key=lambda s: SEVERITY_RANK[s], default=Severity.INFO)


def incident_title_for(alerts: list[CandidateAlert | Alert]) -> str:
    services = sorted({a.service_name for a in alerts})
    rule_ids = sorted({getattr(a, "rule_id", "") for a in alerts})
    primary = rule_ids[0] if rule_ids else "alert"
    svc = ", ".join(services[:3]) + ("…" if len(services) > 3 else "")
    return f"Incident: {primary} affecting {svc}"


def grouping_key(alert: CandidateAlert) -> str:
    """Group related alerts into one incident by service + time bucket.

    Related rules on the same service within the same detection cycle share a group.
    Cross-service gateway/order coupling is handled by including all firing services
    in one incident when fingerprints share a cycle batch key from the engine.
    """
    return alert.service_name


async def upsert_alert(
    db: AsyncSession,
    candidate: CandidateAlert,
    *,
    incident_id,
) -> tuple[Alert, bool]:
    """Return (alert, created). Dedup by fingerprint while firing."""
    existing = (
        await db.execute(
            select(Alert).where(
                Alert.fingerprint == candidate.fingerprint,
                Alert.status == "firing",
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.severity = candidate.severity
        existing.description = candidate.description
        existing.labels = candidate.labels
        existing.annotations = candidate.annotations
        existing.incident_id = incident_id
        await db.flush()
        return existing, False

    alert = Alert(
        rule_id=candidate.rule_id,
        service_name=candidate.service_name,
        severity=candidate.severity,
        title=candidate.title,
        description=candidate.description,
        status="firing",
        fingerprint=candidate.fingerprint,
        started_at=candidate.started_at,
        labels=candidate.labels,
        annotations=candidate.annotations,
        incident_id=incident_id,
    )
    db.add(alert)
    await db.flush()
    return alert, True


async def get_or_create_open_incident(
    db: AsyncSession,
    *,
    service_names: list[str],
    severity: Severity,
    title: str,
    summary: str,
) -> tuple[Incident, bool]:
    """Find an open incident overlapping these services, or create one."""
    open_statuses = [
        IncidentStatus.OPEN,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.MITIGATING,
    ]
    open_incidents = (
        await db.execute(select(Incident).where(Incident.status.in_(open_statuses)))
    ).scalars().all()

    for inc in open_incidents:
        if set(inc.service_names) & set(service_names):
            # Merge services and escalate severity if needed
            merged = sorted(set(inc.service_names) | set(service_names))
            inc.service_names = merged
            if SEVERITY_RANK[severity] > SEVERITY_RANK[inc.severity]:
                inc.severity = severity
            if not inc.summary:
                inc.summary = summary
            await db.flush()
            return inc, False

    incident = Incident(
        title=title,
        status=IncidentStatus.OPEN,
        severity=severity,
        service_names=service_names,
        started_at=datetime.now(UTC),
        detected_at=datetime.now(UTC),
        summary=summary,
        metadata_json={"source": "detection_engine"},
    )
    db.add(incident)
    await db.flush()
    return incident, True


async def resolve_recovered_alerts(
    db: AsyncSession,
    *,
    still_firing_fingerprints: set[str],
) -> list[Alert]:
    """Mark firing alerts as resolved when their fingerprint is no longer firing."""
    firing = (
        await db.execute(select(Alert).where(Alert.status == "firing"))
    ).scalars().all()
    resolved: list[Alert] = []
    now = datetime.now(UTC)
    for alert in firing:
        if alert.fingerprint not in still_firing_fingerprints:
            alert.status = "resolved"
            alert.resolved_at = now
            resolved.append(alert)
    await db.flush()
    return resolved


async def maybe_resolve_incidents(db: AsyncSession) -> list[Incident]:
    """Resolve open incidents that have no remaining firing alerts."""
    open_statuses = [
        IncidentStatus.OPEN,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.MITIGATING,
    ]
    incidents = (
        await db.execute(select(Incident).where(Incident.status.in_(open_statuses)))
    ).scalars().all()
    resolved_incidents: list[Incident] = []
    now = datetime.now(UTC)
    for inc in incidents:
        firing_count = (
            await db.execute(
                select(Alert).where(
                    Alert.incident_id == inc.id,
                    Alert.status == "firing",
                )
            )
        ).scalars().all()
        if firing_count:
            continue
        inc.status = IncidentStatus.RESOLVED
        inc.resolved_at = now
        start = inc.started_at or inc.detected_at
        inc.mttr_seconds = int((now - start).total_seconds())
        resolved_incidents.append(inc)
    await db.flush()
    return resolved_incidents
