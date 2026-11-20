from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sentinelai_contracts import Role, Severity
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, client_meta, require_role
from app.detection.engine import DetectionEngine
from app.detection.rules import DetectionThresholds
from app.models.incident import Alert
from app.models.user import User
from app.schemas.alerts import AlertOut, AnomalyScoreOut, DetectionRunResponse
from app.schemas.common import Page
from app.services.audit import write_audit

router = APIRouter(tags=["alerts"])
EngineerUser = Annotated[User, Depends(require_role(Role.ENGINEER))]


@router.get("/alerts", response_model=Page[AlertOut])
async def list_alerts(
    db: DbSession,
    _user: CurrentUser,
    status: str | None = None,
    service: str | None = None,
    severity: Severity | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[AlertOut]:
    q = select(Alert)
    count_q = select(func.count()).select_from(Alert)
    if status:
        q = q.where(Alert.status == status)
        count_q = count_q.where(Alert.status == status)
    if service:
        q = q.where(Alert.service_name == service)
        count_q = count_q.where(Alert.service_name == service)
    if severity:
        q = q.where(Alert.severity == severity)
        count_q = count_q.where(Alert.severity == severity)
    total = await db.scalar(count_q) or 0
    items = list(
        (
            await db.execute(
                q.order_by(Alert.started_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.post("/alerts/evaluate", response_model=DetectionRunResponse)
async def evaluate_alerts(
    request: Request,
    db: DbSession,
    user: EngineerUser,
) -> DetectionRunResponse:
    """Run one detection cycle (rules + anomaly + lifecycle)."""
    engine = DetectionEngine(DetectionThresholds())
    result = await engine.run(db)
    meta = client_meta(request)
    await write_audit(
        db,
        action="detection.evaluate",
        actor_user_id=user.id,
        resource_type="detection",
        resource_id="cycle",
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={
            "candidates": len(result.candidates),
            "alerts_created": result.alerts_created,
            "incidents_created": result.incidents_created,
        },
    )
    return DetectionRunResponse(
        evaluated_at=result.evaluated_at,
        services_checked=result.services_checked,
        candidates=len(result.candidates),
        alerts_created=result.alerts_created,
        alerts_updated=result.alerts_updated,
        alerts_resolved=result.alerts_resolved,
        incidents_created=result.incidents_created,
        incidents_updated=result.incidents_updated,
        incidents_resolved=result.incidents_resolved,
        incident_ids=list(dict.fromkeys(result.incident_ids)),
        anomaly_scores=[
            AnomalyScoreOut(
                metric_name=s.metric_name,
                service_name=s.service_name,
                value=s.value,
                baseline_mean=s.baseline_mean,
                baseline_std=s.baseline_std,
                sample_count=s.sample_count,
                z_score=s.z_score,
                is_anomalous=s.is_anomalous,
                severity_hint=s.severity_hint,
                explanation=s.explanation,
            )
            for s in result.anomaly_scores
        ],
    )


@router.get("/incidents/{incident_id}/timeline")
async def incident_timeline(
    incident_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> dict[str, Any]:
    alerts = list(
        (
            await db.execute(
                select(Alert)
                .where(Alert.incident_id == incident_id)
                .order_by(Alert.started_at)
            )
        )
        .scalars()
        .all()
    )
    events: list[dict[str, Any]] = []
    for alert in alerts:
        events.append(
            {
                "type": "alert_firing",
                "timestamp": alert.started_at.isoformat(),
                "title": alert.title,
                "severity": alert.severity.value,
                "rule_id": alert.rule_id,
                "service_name": alert.service_name,
                "alert_id": str(alert.id),
            }
        )
        if alert.resolved_at:
            events.append(
                {
                    "type": "alert_resolved",
                    "timestamp": alert.resolved_at.isoformat(),
                    "title": f"Resolved: {alert.title}",
                    "severity": alert.severity.value,
                    "rule_id": alert.rule_id,
                    "service_name": alert.service_name,
                    "alert_id": str(alert.id),
                }
            )
    events.sort(key=lambda e: e["timestamp"])
    return {
        "incident_id": str(incident_id),
        "events": events,
        "generated_at": datetime.now(UTC).isoformat(),
    }
