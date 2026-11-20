from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sentinelai_contracts import Role
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, client_meta, require_role
from app.core.errors import AppError
from app.models.remediation import RemediationExecution, RemediationPlan
from app.models.user import User
from app.remediation import service as remediation_service
from app.schemas.common import APIModel, Page
from app.services.audit import write_audit

router = APIRouter(prefix="/remediations", tags=["remediations"])
EngineerUser = Annotated[User, Depends(require_role(Role.ENGINEER))]


class RemediationOut(APIModel):
    id: UUID
    investigation_id: UUID
    incident_id: UUID
    status: str
    problem_summary: str
    rationale: str
    actions: list[dict[str, Any]]
    risks: str
    rollback_steps: list[Any]
    expected_impact: str
    created_at: object


class DecisionBody(APIModel):
    reason: str | None = None


@router.get("", response_model=Page[RemediationOut])
async def list_remediations(
    db: DbSession,
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[RemediationOut]:
    total = await db.scalar(select(func.count()).select_from(RemediationPlan)) or 0
    items = list(
        (
            await db.execute(
                select(RemediationPlan)
                .order_by(RemediationPlan.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return Page(items=[_out(p) for p in items], page=page, page_size=page_size, total=total)


@router.get("/{remediation_id}", response_model=RemediationOut)
async def get_remediation(
    remediation_id: UUID, db: DbSession, _user: CurrentUser
) -> RemediationOut:
    plan = await remediation_service.get_plan(db, remediation_id)
    return _out(plan)


@router.post("/{remediation_id}/approve", response_model=RemediationOut)
async def approve_remediation(
    remediation_id: UUID,
    request: Request,
    db: DbSession,
    user: EngineerUser,
    body: DecisionBody | None = None,
) -> RemediationOut:
    body = body or DecisionBody()
    plan, execution = await remediation_service.approve_and_execute(
        db, remediation_id, user=user, reason=body.reason
    )
    meta = client_meta(request)
    await write_audit(
        db,
        action="remediation.approve_execute",
        actor_user_id=user.id,
        resource_type="remediation_plan",
        resource_id=str(plan.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={
            "execution_id": str(execution.id),
            "execution_status": execution.status,
            "sandbox": True,
        },
    )
    return _out(plan)


@router.post("/{remediation_id}/reject", response_model=RemediationOut)
async def reject_remediation(
    remediation_id: UUID,
    request: Request,
    db: DbSession,
    user: EngineerUser,
    body: DecisionBody | None = None,
) -> RemediationOut:
    body = body or DecisionBody()
    plan = await remediation_service.reject_plan(
        db, remediation_id, user=user, reason=body.reason
    )
    meta = client_meta(request)
    await write_audit(
        db,
        action="remediation.reject",
        actor_user_id=user.id,
        resource_type="remediation_plan",
        resource_id=str(plan.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"reason": body.reason},
    )
    return _out(plan)


@router.post("/{remediation_id}/cancel", response_model=RemediationOut)
async def cancel_remediation(
    remediation_id: UUID,
    request: Request,
    db: DbSession,
    user: EngineerUser,
    body: DecisionBody | None = None,
) -> RemediationOut:
    body = body or DecisionBody()
    plan = await remediation_service.cancel_plan(
        db, remediation_id, user=user, reason=body.reason
    )
    meta = client_meta(request)
    await write_audit(
        db,
        action="remediation.cancel",
        actor_user_id=user.id,
        resource_type="remediation_plan",
        resource_id=str(plan.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return _out(plan)


@router.get("/{remediation_id}/execution")
async def get_execution(
    remediation_id: UUID, db: DbSession, _user: CurrentUser
) -> dict[str, Any]:
    await remediation_service.get_plan(db, remediation_id)
    execution = (
        await db.execute(
            select(RemediationExecution)
            .where(RemediationExecution.plan_id == remediation_id)
            .order_by(RemediationExecution.started_at.desc())
        )
    ).scalars().first()
    if execution is None:
        raise AppError("NOT_FOUND", "No execution for this plan", status_code=404)
    return {
        "id": str(execution.id),
        "plan_id": str(execution.plan_id),
        "status": execution.status,
        "result": execution.result,
        "rollback_status": execution.rollback_status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
    }


def _out(plan: RemediationPlan) -> RemediationOut:
    return RemediationOut(
        id=plan.id,
        investigation_id=plan.investigation_id,
        incident_id=plan.incident_id,
        status=plan.status.value,
        problem_summary=plan.problem_summary,
        rationale=plan.rationale,
        actions=list(plan.actions or []),
        risks=plan.risks,
        rollback_steps=list(plan.rollback_steps or []),
        expected_impact=plan.expected_impact,
        created_at=plan.created_at,
    )
