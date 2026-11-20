"""Control-plane proxy for simulator scenarios (engineer+)."""

from typing import Annotated, Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sentinelai_contracts import Role

from app.core.config import get_settings
from app.core.deps import DbSession, client_meta, require_role
from app.core.errors import AppError
from app.models.user import User
from app.schemas.common import APIModel
from app.services.audit import write_audit

router = APIRouter(prefix="/simulator", tags=["simulator"])
EngineerUser = Annotated[User, Depends(require_role(Role.ENGINEER))]

SERVICE_URLS = {
    "api-gateway": "GATEWAY_URL",
    "user-service": "USER_SERVICE_URL",
    "order-service": "ORDER_SERVICE_URL",
    "payment-service": "PAYMENT_SERVICE_URL",
}

SCENARIO_CATALOG = [
    {"name": "slow_db_queries", "description": "Injects artificial DB query latency"},
    {"name": "http_500_spike", "description": "Raises HTTP 500 error rate"},
    {"name": "redis_connection_failure", "description": "Simulates Redis connection failures"},
    {"name": "memory_pressure", "description": "Reports elevated memory utilization"},
    {"name": "increased_latency", "description": "Increases end-to-end latency"},
    {"name": "dependency_timeout", "description": "Simulates dependency timeouts"},
    {"name": "failed_background_jobs", "description": "Fails periodic background jobs"},
    {"name": "bad_deployment", "description": "Regression after a bad deploy"},
]


class ScenarioRunRequest(APIModel):
    seed: int = 42
    duration_seconds: int = Field(default=60, ge=5, le=3600)
    services: list[str] | None = None


class ScenarioRunResponse(APIModel):
    run_id: str
    scenario: str
    seed: int
    duration_seconds: int
    status: str
    targets: list[dict[str, Any]]


def _service_base_urls() -> dict[str, str]:
    import os

    defaults = {
        "api-gateway": "http://localhost:8100",
        "user-service": "http://localhost:8101",
        "order-service": "http://localhost:8102",
        "payment-service": "http://localhost:8103",
    }
    return {
        "api-gateway": os.getenv("GATEWAY_URL", defaults["api-gateway"]),
        "user-service": os.getenv("USER_SERVICE_URL", defaults["user-service"]),
        "order-service": os.getenv("ORDER_SERVICE_URL", defaults["order-service"]),
        "payment-service": os.getenv("PAYMENT_SERVICE_URL", defaults["payment-service"]),
    }


@router.get("/scenarios")
async def list_scenarios(_user: EngineerUser) -> dict[str, Any]:
    return {"items": SCENARIO_CATALOG}


@router.post("/scenarios/{name}/run", response_model=ScenarioRunResponse, status_code=202)
async def run_scenario(
    name: str,
    body: ScenarioRunRequest,
    request: Request,
    db: DbSession,
    user: EngineerUser,
) -> ScenarioRunResponse:
    if name not in {s["name"] for s in SCENARIO_CATALOG}:
        raise AppError("NOT_FOUND", "Unknown scenario", status_code=404)
    urls = _service_base_urls()
    targets = body.services or list(urls.keys())
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for svc in targets:
            base = urls.get(svc)
            if not base:
                results.append({"service": svc, "status": "skipped", "reason": "unknown service"})
                continue
            try:
                resp = await client.post(
                    f"{base}/scenarios/{name}/run",
                    json={"seed": body.seed, "duration_seconds": body.duration_seconds},
                )
                results.append(
                    {
                        "service": svc,
                        "status": "ok" if resp.status_code < 400 else "error",
                        "response": resp.json() if resp.status_code < 500 else {"raw": resp.text},
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append({"service": svc, "status": "unreachable", "error": str(exc)})

    meta = client_meta(request)
    run_id = str(uuid4())
    await write_audit(
        db,
        action="simulator.scenario.run",
        actor_user_id=user.id,
        resource_type="scenario",
        resource_id=name,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"run_id": run_id, "seed": body.seed, "duration_seconds": body.duration_seconds},
    )
    return ScenarioRunResponse(
        run_id=run_id,
        scenario=name,
        seed=body.seed,
        duration_seconds=body.duration_seconds,
        status="started",
        targets=results,
    )


@router.post("/scenarios/stop")
async def stop_scenarios(request: Request, db: DbSession, user: EngineerUser) -> dict[str, Any]:
    urls = _service_base_urls()
    results = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for svc, base in urls.items():
            try:
                resp = await client.post(f"{base}/scenarios/stop")
                results.append({"service": svc, "status": resp.status_code})
            except Exception as exc:  # noqa: BLE001
                results.append({"service": svc, "status": "unreachable", "error": str(exc)})
    meta = client_meta(request)
    await write_audit(
        db,
        action="simulator.scenario.stop",
        actor_user_id=user.id,
        resource_type="scenario",
        resource_id="*",
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"results": results},
    )
    _ = get_settings()
    return {"status": "stopped", "targets": results}
