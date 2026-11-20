from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sentinelai_contracts import IncidentStatus, Role, Severity
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, client_meta, require_role
from app.core.errors import AppError
from app.models.incident import Incident
from app.models.user import User
from app.schemas.common import Page
from app.schemas.incidents import IncidentOut, IncidentUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/incidents", tags=["incidents"])
EngineerUser = Annotated[User, Depends(require_role(Role.ENGINEER))]


@router.get("", response_model=Page[IncidentOut])
async def list_incidents(
    db: DbSession,
    _user: CurrentUser,
    status: IncidentStatus | None = None,
    severity: Severity | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[IncidentOut]:
    q = select(Incident)
    count_q = select(func.count()).select_from(Incident)
    if status:
        q = q.where(Incident.status == status)
        count_q = count_q.where(Incident.status == status)
    if severity:
        q = q.where(Incident.severity == severity)
        count_q = count_q.where(Incident.severity == severity)
    total = await db.scalar(count_q) or 0
    q = q.order_by(Incident.detected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(q)).scalars().all())
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: UUID, db: DbSession, _user: CurrentUser) -> Incident:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise AppError("NOT_FOUND", "Incident not found", status_code=404)
    return incident


@router.patch("/{incident_id}", response_model=IncidentOut)
async def update_incident(
    incident_id: UUID,
    body: IncidentUpdate,
    request: Request,
    db: DbSession,
    user: EngineerUser,
) -> Incident:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise AppError("NOT_FOUND", "Incident not found", status_code=404)

    if body.summary is not None:
        incident.summary = body.summary
    if body.status is not None:
        incident.status = body.status
        if body.status == IncidentStatus.RESOLVED and incident.resolved_at is None:
            incident.resolved_at = datetime.now(UTC)
            start = incident.started_at or incident.detected_at
            incident.mttr_seconds = int((incident.resolved_at - start).total_seconds())

    meta = client_meta(request)
    await write_audit(
        db,
        action="incident.update",
        actor_user_id=user.id,
        resource_type="incident",
        resource_id=str(incident.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"status": incident.status.value},
    )
    await db.flush()
    return incident
