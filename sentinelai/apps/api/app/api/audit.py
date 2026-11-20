from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sentinelai_contracts import Role
from sqlalchemy import func, select

from app.core.deps import DbSession, require_role
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.common import APIModel, Page

router = APIRouter(prefix="/audit", tags=["audit"])
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]


class AuditOut(APIModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict
    created_at: object


@router.get("", response_model=Page[AuditOut])
async def list_audit(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = None,
) -> Page[AuditOut]:
    q = select(AuditEvent)
    count_q = select(func.count()).select_from(AuditEvent)
    if action:
        q = q.where(AuditEvent.action == action)
        count_q = count_q.where(AuditEvent.action == action)
    total = await db.scalar(count_q) or 0
    q = q.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(q)).scalars().all())
    return Page(items=items, page=page, page_size=page_size, total=total)
