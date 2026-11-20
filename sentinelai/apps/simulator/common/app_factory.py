from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from common.config import SimulatorSettings
from common.failures import FAILURES, SCENARIO_CATALOG
from common.telemetry import TelemetryEmitter

logger = logging.getLogger(__name__)

REQUESTS = Counter(
    "sim_http_requests_total",
    "Total HTTP requests",
    ["service", "path", "status"],
)
LATENCY = Histogram(
    "sim_http_request_duration_seconds",
    "Request latency",
    ["service", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
CPU_GAUGE = Gauge("sim_cpu_percent", "Simulated CPU percent", ["service"])
MEM_GAUGE = Gauge("sim_memory_percent", "Simulated memory percent", ["service"])


def create_service_app(service_name: str, port: int, handlers: dict[str, Any] | None = None) -> FastAPI:
    settings = SimulatorSettings(service_name=service_name, port=port)
    emitter = TelemetryEmitter(settings)
    handlers = handlers or {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(_traffic_loop(settings, emitter))
        yield
        task.cancel()
        await emitter.close()

    app = FastAPI(title=f"SENTINELAI Simulator — {service_name}", lifespan=lifespan)
    app.state.settings = settings
    app.state.emitter = emitter

    @app.get("/health")
    async def health() -> dict[str, str]:
        sc = FAILURES.current()
        status = "degraded" if sc else "healthy"
        return {"status": status, "service": service_name}

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/scenarios")
    async def list_scenarios() -> dict[str, Any]:
        current = FAILURES.current()
        return {
            "catalog": SCENARIO_CATALOG,
            "active": None
            if not current
            else {
                "name": current.name,
                "seed": current.seed,
                "duration_seconds": current.duration_seconds,
                "remaining": current.remaining,
            },
        }

    @app.post("/scenarios/{name}/run")
    async def run_scenario(name: str, body: dict[str, Any]) -> dict[str, Any]:
        names = {s["name"] for s in SCENARIO_CATALOG}
        if name not in names:
            raise HTTPException(status_code=404, detail="Unknown scenario")
        seed = int(body.get("seed", 42))
        duration = int(body.get("duration_seconds", 60))
        params = body.get("params") or next(
            (s["default_params"] for s in SCENARIO_CATALOG if s["name"] == name), {}
        )
        sc = FAILURES.start(name, seed=seed, duration_seconds=duration, **params)
        if name == "bad_deployment":
            await emitter.emit_deployment(
                version=f"bad-{seed}",
                notes="Injected regression deployment for demo",
            )
        await emitter.emit_log(
            "WARN",
            f"Scenario started: {name} seed={seed} duration={duration}s",
            correlation_id=str(uuid.uuid4()),
            attributes={"scenario": name, "seed": seed},
        )
        return {
            "run_id": str(uuid.uuid4()),
            "scenario": name,
            "seed": seed,
            "duration_seconds": duration,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
            "remaining": sc.remaining,
        }

    @app.post("/scenarios/stop")
    async def stop_scenario() -> dict[str, str]:
        FAILURES.stop()
        await emitter.emit_log("INFO", "Scenario stopped")
        return {"status": "stopped"}

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        if request.url.path in {"/metrics", "/health"}:
            return await call_next(request)
        start = time.perf_counter()
        extra_ms = FAILURES.extra_latency_ms()
        if extra_ms:
            await asyncio.sleep(extra_ms / 1000.0)
        if FAILURES.should_http_500() and request.url.path.startswith("/api"):
            duration = time.perf_counter() - start
            REQUESTS.labels(service_name, request.url.path, "500").inc()
            LATENCY.labels(service_name, request.url.path).observe(duration)
            trace_id = await emitter.emit_trace(
                operation=request.url.path,
                duration_ms=duration * 1000,
                status="error",
            )
            await emitter.emit_log(
                "ERROR",
                f"Injected HTTP 500 for {request.url.path}",
                trace_id=trace_id,
                attributes={"injected": True},
            )
            raise HTTPException(status_code=500, detail="Injected failure")
        response = await call_next(request)
        duration = time.perf_counter() - start
        REQUESTS.labels(service_name, request.url.path, str(response.status_code)).inc()
        LATENCY.labels(service_name, request.url.path).observe(duration)
        return response

    # Domain routes
    for path, handler in handlers.items():
        app.add_api_route(path, handler, methods=["GET", "POST"])

    return app


async def _traffic_loop(settings: SimulatorSettings, emitter: TelemetryEmitter) -> None:
    """Emit periodic metric samples so overview/detection have real data."""
    while True:
        try:
            sc = FAILURES.current()
            cpu = 35.0
            mem = 48.0
            rps = 12.0
            err = 0.01
            p50, p95, p99 = 40.0, 120.0, 220.0
            if sc:
                if sc.name == "memory_pressure":
                    mem = float(sc.params.get("memory_percent", 92.0))
                if sc.name in {"http_500_spike", "bad_deployment"}:
                    err = float(sc.params.get("error_rate", 0.4))
                    cpu = 70.0
                if sc.name in {"increased_latency", "slow_db_queries", "dependency_timeout"}:
                    mult = float(sc.params.get("latency_multiplier", 5.0))
                    p50, p95, p99 = 40 * mult, 120 * mult, 220 * mult
                    cpu = 65.0
                if sc.name == "failed_background_jobs":
                    await emitter.emit_log(
                        "ERROR",
                        "Background job failed: reconcile_orders",
                        attributes={"job": "reconcile_orders", "injected": True},
                    )
                if sc.name == "redis_connection_failure":
                    await emitter.emit_log(
                        "ERROR",
                        "Redis connection refused",
                        attributes={"dependency": "redis", "injected": True},
                    )
                    err = max(err, 0.2)

            CPU_GAUGE.labels(settings.service_name).set(cpu)
            MEM_GAUGE.labels(settings.service_name).set(mem)
            await emitter.emit_metrics(
                [
                    {"metric_name": "http_requests_per_second", "value": rps, "labels": {}},
                    {"metric_name": "http_error_rate", "value": err, "labels": {}},
                    {"metric_name": "http_latency_p50_ms", "value": p50, "labels": {}},
                    {"metric_name": "http_latency_p95_ms", "value": p95, "labels": {}},
                    {"metric_name": "http_latency_p99_ms", "value": p99, "labels": {}},
                    {"metric_name": "cpu_percent", "value": cpu, "labels": {}},
                    {"metric_name": "memory_percent", "value": mem, "labels": {}},
                ]
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("traffic loop error: %s", exc)
        await asyncio.sleep(settings.traffic_interval_seconds)
