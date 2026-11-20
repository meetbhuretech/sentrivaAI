from fastapi import APIRouter

from app.api import (
    alerts,
    audit,
    auth,
    evaluation,
    incidents,
    investigations,
    overview,
    remediations,
    services,
    simulator,
    telemetry,
)
from app.mcp.server import router as mcp_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(overview.router)
api_router.include_router(services.router)
api_router.include_router(incidents.router)
api_router.include_router(alerts.router)
api_router.include_router(investigations.router)
api_router.include_router(remediations.router)
api_router.include_router(evaluation.router)
api_router.include_router(telemetry.router)
api_router.include_router(simulator.router)
api_router.include_router(audit.router)
api_router.include_router(mcp_router)


@api_router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentinelai-api"}
