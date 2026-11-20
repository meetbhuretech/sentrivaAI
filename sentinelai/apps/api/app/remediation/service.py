from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sentinelai_contracts import RemediationStatus
from sentinelai_contracts.enums import REMEDIATION_ACTION_ALLOWLIST
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.remediation import RemediationApproval, RemediationExecution, RemediationPlan
from app.models.user import User
from app.remediation.sandbox import SandboxExecutor


async def get_plan(db: AsyncSession, plan_id: UUID) -> RemediationPlan:
    plan = (
        await db.execute(select(RemediationPlan).where(RemediationPlan.id == plan_id))
    ).scalar_one_or_none()
    if plan is None:
        raise AppError("NOT_FOUND", "Remediation plan not found", status_code=404)
    return plan


def _validate_actions(actions: list) -> None:
    for action in actions:
        action_type = action.get("action_type") if isinstance(action, dict) else None
        if action_type not in REMEDIATION_ACTION_ALLOWLIST:
            raise AppError(
                "INVALID_ACTION",
                f"Action '{action_type}' is not allowlisted",
                status_code=400,
                details={"allowlist": sorted(REMEDIATION_ACTION_ALLOWLIST)},
            )


async def approve_and_execute(
    db: AsyncSession,
    plan_id: UUID,
    *,
    user: User,
    reason: str | None = None,
) -> tuple[RemediationPlan, RemediationExecution]:
    plan = await get_plan(db, plan_id)
    if plan.status != RemediationStatus.PROPOSED:
        raise AppError(
            "CONFLICT",
            f"Plan status is {plan.status.value}; only proposed plans can be approved",
            status_code=409,
        )
    _validate_actions(plan.actions or [])

    db.add(
        RemediationApproval(
            plan_id=plan.id,
            approver_user_id=user.id,
            decision="approved",
            reason=reason,
        )
    )
    plan.status = RemediationStatus.APPROVED
    await db.flush()

    plan.status = RemediationStatus.EXECUTING
    execution = RemediationExecution(
        plan_id=plan.id,
        status="running",
        result={},
        started_at=datetime.now(UTC),
    )
    db.add(execution)
    await db.flush()

    sandbox = SandboxExecutor()
    result = await sandbox.execute(list(plan.actions or []))
    execution.result = result
    execution.completed_at = datetime.now(UTC)
    if result.get("overall_status") == "succeeded":
        execution.status = "succeeded"
        plan.status = RemediationStatus.SUCCEEDED
        execution.rollback_status = "not_needed"
    else:
        execution.status = "failed"
        plan.status = RemediationStatus.FAILED
        execution.rollback_status = "available"
    await db.flush()
    return plan, execution


async def reject_plan(
    db: AsyncSession,
    plan_id: UUID,
    *,
    user: User,
    reason: str | None = None,
) -> RemediationPlan:
    plan = await get_plan(db, plan_id)
    if plan.status != RemediationStatus.PROPOSED:
        raise AppError("CONFLICT", f"Plan status is {plan.status.value}", status_code=409)
    db.add(
        RemediationApproval(
            plan_id=plan.id,
            approver_user_id=user.id,
            decision="rejected",
            reason=reason,
        )
    )
    plan.status = RemediationStatus.REJECTED
    await db.flush()
    return plan


async def cancel_plan(
    db: AsyncSession,
    plan_id: UUID,
    *,
    user: User,
    reason: str | None = None,
) -> RemediationPlan:
    plan = await get_plan(db, plan_id)
    if plan.status not in {RemediationStatus.PROPOSED, RemediationStatus.APPROVED}:
        raise AppError("CONFLICT", f"Plan status is {plan.status.value}", status_code=409)
    db.add(
        RemediationApproval(
            plan_id=plan.id,
            approver_user_id=user.id,
            decision="cancelled",
            reason=reason,
        )
    )
    plan.status = RemediationStatus.CANCELLED
    await db.flush()
    return plan
