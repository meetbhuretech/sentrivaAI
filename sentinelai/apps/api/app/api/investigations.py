import asyncio
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sentinelai_contracts import Role
from sqlalchemy import func, select

from app.agents.orchestrator import InvestigationOrchestrator
from app.api.sse import sse_pack, user_from_access_token
from app.core.database import AsyncSessionLocal
from app.core.deps import CurrentUser, DbSession, client_meta, require_role
from app.core.errors import AppError
from app.models.investigation import AgentFinding, Hypothesis, Investigation, InvestigationCheckpoint
from app.models.user import User
from app.schemas.common import Page
from app.schemas.investigations import (
    InvestigationEvidenceOut,
    InvestigationOut,
    StartInvestigationRequest,
)
from app.services.audit import write_audit

router = APIRouter(tags=["investigations"])
EngineerUser = Annotated[User, Depends(require_role(Role.ENGINEER))]


@router.get("/investigations", response_model=Page[InvestigationOut])
async def list_investigations(
    db: DbSession,
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[InvestigationOut]:
    total = await db.scalar(select(func.count()).select_from(Investigation)) or 0
    items = list(
        (
            await db.execute(
                select(Investigation)
                .order_by(Investigation.started_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return Page(
        items=[_to_out(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/investigations/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: UUID, db: DbSession, _user: CurrentUser
) -> InvestigationOut:
    inv = await _get(db, investigation_id)
    return _to_out(inv)


@router.get("/investigations/{investigation_id}/stream")
async def investigation_stream(
    investigation_id: UUID,
    _user: Annotated[User, Depends(user_from_access_token)],
) -> StreamingResponse:
    async def events():
        while True:
            async with AsyncSessionLocal() as db:
                inv = (
                    await db.execute(
                        select(Investigation).where(Investigation.id == investigation_id)
                    )
                ).scalar_one_or_none()
                if inv is None:
                    yield sse_pack("error", {"message": "Investigation not found"})
                    return
                checkpoints = list(
                    (
                        await db.execute(
                            select(InvestigationCheckpoint)
                            .where(
                                InvestigationCheckpoint.investigation_id == investigation_id
                            )
                            .order_by(InvestigationCheckpoint.created_at)
                        )
                    )
                    .scalars()
                    .all()
                )
                payload = {
                    "investigation": _to_out(inv).model_dump(mode="json"),
                    "events": [
                        {
                            "step": c.step,
                            "timestamp": c.created_at.isoformat(),
                            "type": "checkpoint",
                        }
                        for c in checkpoints
                    ],
                }
                terminal = inv.status.value in {
                    "completed",
                    "failed",
                    "cancelled",
                    "timed_out",
                }
            yield sse_pack("investigation", payload)
            if terminal:
                return
            await asyncio.sleep(2)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/investigations/{investigation_id}/timeline")
async def investigation_timeline(
    investigation_id: UUID, db: DbSession, _user: CurrentUser
) -> dict[str, Any]:
    await _get(db, investigation_id)
    checkpoints = list(
        (
            await db.execute(
                select(InvestigationCheckpoint)
                .where(InvestigationCheckpoint.investigation_id == investigation_id)
                .order_by(InvestigationCheckpoint.created_at)
            )
        )
        .scalars()
        .all()
    )
    return {
        "investigation_id": str(investigation_id),
        "events": [
            {
                "step": c.step,
                "timestamp": c.created_at.isoformat(),
                "type": "checkpoint",
            }
            for c in checkpoints
        ],
    }


@router.get("/investigations/{investigation_id}/evidence", response_model=InvestigationEvidenceOut)
async def investigation_evidence(
    investigation_id: UUID, db: DbSession, _user: CurrentUser
) -> InvestigationEvidenceOut:
    inv = await _get(db, investigation_id)
    findings = list(
        (
            await db.execute(
                select(AgentFinding).where(AgentFinding.investigation_id == investigation_id)
            )
        )
        .scalars()
        .all()
    )
    hyps = list(
        (
            await db.execute(
                select(Hypothesis)
                .where(Hypothesis.investigation_id == investigation_id)
                .order_by(Hypothesis.rank)
            )
        )
        .scalars()
        .all()
    )
    tool_calls = (inv.state or {}).get("tool_calls", [])
    return InvestigationEvidenceOut(
        findings=[
            {
                "id": str(f.id),
                "agent_name": f.agent_name,
                "summary": f.summary,
                "details": f.details,
                "evidence_refs": f.evidence_refs,
                "source": f.source,
            }
            for f in findings
        ],
        hypotheses=[
            {
                "id": str(h.id),
                "statement": h.statement,
                "rank": h.rank,
                "confidence": h.confidence,
                "evidence_refs": h.evidence_refs,
                "grounded": h.grounded,
                "evaluation_notes": h.evaluation_notes,
            }
            for h in hyps
        ],
        tool_calls=tool_calls,
    )


@router.post("/incidents/{incident_id}/investigate", response_model=InvestigationOut, status_code=202)
async def start_investigation(
    incident_id: UUID,
    request: Request,
    db: DbSession,
    user: EngineerUser,
    body: StartInvestigationRequest | None = None,
) -> InvestigationOut:
    body = body or StartInvestigationRequest()
    orch = InvestigationOrchestrator(db)
    try:
        inv = await orch.start(
            incident_id, provider_name=body.provider, model=body.model
        )
    except ValueError as exc:
        raise AppError("NOT_FOUND", str(exc), status_code=404) from exc
    meta = client_meta(request)
    await write_audit(
        db,
        action="investigation.start",
        actor_user_id=user.id,
        resource_type="investigation",
        resource_id=str(inv.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"incident_id": str(incident_id), "provider": inv.provider, "model": inv.model},
    )
    return _to_out(inv)


@router.post("/investigations/{investigation_id}/cancel", response_model=InvestigationOut)
async def cancel_investigation(
    investigation_id: UUID,
    request: Request,
    db: DbSession,
    user: EngineerUser,
) -> InvestigationOut:
    from datetime import UTC, datetime

    from sentinelai_contracts import InvestigationStatus

    inv = await _get(db, investigation_id)
    if inv.status in {
        InvestigationStatus.COMPLETED,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
        InvestigationStatus.TIMED_OUT,
    }:
        raise AppError("CONFLICT", f"Investigation already {inv.status.value}", status_code=409)
    inv.status = InvestigationStatus.CANCELLED
    inv.current_step = "cancelled"
    inv.completed_at = datetime.now(UTC)
    meta = client_meta(request)
    await write_audit(
        db,
        action="investigation.cancel",
        actor_user_id=user.id,
        resource_type="investigation",
        resource_id=str(inv.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    await db.flush()
    return _to_out(inv)


async def _get(db: DbSession, investigation_id: UUID) -> Investigation:
    inv = (
        await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    ).scalar_one_or_none()
    if inv is None:
        raise AppError("NOT_FOUND", "Investigation not found", status_code=404)
    return inv


def _to_out(inv: Investigation) -> InvestigationOut:
    return InvestigationOut(
        id=inv.id,
        incident_id=inv.incident_id,
        status=inv.status,
        current_step=inv.current_step,
        provider=inv.provider,
        model=inv.model,
        prompt_version=inv.prompt_version,
        rca=inv.rca,
        token_usage=inv.token_usage or {},
        estimated_cost_usd=float(inv.estimated_cost_usd or 0),
        started_at=inv.started_at,
        completed_at=inv.completed_at,
        error_message=inv.error_message,
    )
