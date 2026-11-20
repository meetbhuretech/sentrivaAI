import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.errors import AppError, app_error_handler, http_error_handler
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.detection.scheduler import detection_loop
from app.services.bootstrap import ensure_bootstrap_admin, ensure_default_services


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    async with AsyncSessionLocal() as session:
        await ensure_bootstrap_admin(session)
        await ensure_default_services(session)
        await session.commit()
    task: asyncio.Task | None = None
    if os.getenv("ENABLE_DETECTION_SCHEDULER", "true").lower() in {"1", "true", "yes"}:
        interval = float(os.getenv("DETECTION_INTERVAL_SECONDS", "30"))
        task = asyncio.create_task(detection_loop(interval_seconds=interval))
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Simulator-Token"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)

    app.include_router(api_router)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
