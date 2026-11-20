from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sentinelai_contracts import Role
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, client_meta, require_role
from app.core.errors import AppError
from app.evaluation.runner import load_manifest, run_evaluation
from app.models.evaluation import EvaluationRun, EvaluationRunResult
from app.models.user import User
from app.schemas.common import APIModel, Page
from app.services.audit import write_audit

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
EngineerUser = Annotated[User, Depends(require_role(Role.ENGINEER))]


class StartEvaluationRequest(APIModel):
    dataset_version: str = "v1"
    provider: str = "deterministic"
    model: str = "rules-v1"
    prompt_version: str = "v1"


class EvaluationRunOut(APIModel):
    id: UUID
    dataset_version: str
    provider: str
    model: str
    prompt_version: str
    status: str
    metrics: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


@router.get("/datasets")
async def list_datasets(_user: CurrentUser) -> dict[str, Any]:
    try:
        manifest = load_manifest()
    except FileNotFoundError:
        return {"items": []}
    return {
        "items": [
            {
                "dataset_version": manifest["dataset_version"],
                "description": manifest.get("description"),
                "case_count": len(manifest.get("cases", [])),
                "human_review_process": manifest.get("human_review_process"),
            }
        ]
    }


@router.get("/runs", response_model=Page[EvaluationRunOut])
async def list_runs(
    db: DbSession,
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[EvaluationRunOut]:
    total = await db.scalar(select(func.count()).select_from(EvaluationRun)) or 0
    items = list(
        (
            await db.execute(
                select(EvaluationRun)
                .order_by(EvaluationRun.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.post("/runs", response_model=EvaluationRunOut, status_code=202)
async def start_run(
    body: StartEvaluationRequest,
    request: Request,
    db: DbSession,
    user: EngineerUser,
) -> EvaluationRun:
    run = await run_evaluation(
        db,
        dataset_version=body.dataset_version,
        provider=body.provider,
        model=body.model,
        prompt_version=body.prompt_version,
    )
    meta = client_meta(request)
    await write_audit(
        db,
        action="evaluation.run",
        actor_user_id=user.id,
        resource_type="evaluation_run",
        resource_id=str(run.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"provider": body.provider, "model": body.model, "dataset": body.dataset_version},
    )
    return run


@router.get("/runs/{run_id}", response_model=EvaluationRunOut)
async def get_run(run_id: UUID, db: DbSession, _user: CurrentUser) -> EvaluationRun:
    run = (
        await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    ).scalar_one_or_none()
    if run is None:
        raise AppError("NOT_FOUND", "Evaluation run not found", status_code=404)
    return run


@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: UUID, db: DbSession, _user: CurrentUser) -> dict[str, Any]:
    rows = list(
        (
            await db.execute(
                select(EvaluationRunResult).where(EvaluationRunResult.run_id == run_id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "case_id": r.case_id,
                "passed": r.passed,
                "scores": r.scores,
                "details": r.details,
            }
            for r in rows
        ]
    }


@router.get("/comparisons")
async def comparisons(db: DbSession, _user: CurrentUser) -> dict[str, Any]:
    """Compare completed runs that share the same dataset version."""
    runs = list(
        (
            await db.execute(
                select(EvaluationRun)
                .where(EvaluationRun.status == "completed")
                .order_by(EvaluationRun.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_dataset.setdefault(run.dataset_version, []).append(
            {
                "id": str(run.id),
                "provider": run.provider,
                "model": run.model,
                "prompt_version": run.prompt_version,
                "metrics": run.metrics,
                "created_at": run.created_at.isoformat(),
            }
        )
    return {"datasets": by_dataset}
