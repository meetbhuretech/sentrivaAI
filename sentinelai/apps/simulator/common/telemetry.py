from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from common.config import SimulatorSettings

logger = logging.getLogger(__name__)


class TelemetryEmitter:
    def __init__(self, settings: SimulatorSettings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=5.0)

    def _headers(self) -> dict[str, str]:
        return {"X-Simulator-Token": self.settings.simulator_token}

    async def close(self) -> None:
        await self._client.aclose()

    async def emit_log(
        self,
        level: str,
        message: str,
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
        correlation_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "logs": [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "service_name": self.settings.service_name,
                    "environment": self.settings.environment,
                    "level": level,
                    "message": message,
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "correlation_id": correlation_id,
                    "attributes": attributes or {},
                }
            ]
        }
        await self._post("/telemetry/logs", payload)

    async def emit_metrics(self, metrics: list[dict[str, Any]]) -> None:
        now = datetime.now(UTC).isoformat()
        payload = {
            "metrics": [
                {
                    "timestamp": now,
                    "service_name": self.settings.service_name,
                    **m,
                }
                for m in metrics
            ]
        }
        await self._post("/telemetry/metrics", payload)

    async def emit_trace(
        self,
        *,
        operation: str,
        duration_ms: float,
        status: str = "ok",
        spans: list[dict[str, Any]] | None = None,
    ) -> str:
        trace_id = uuid.uuid4().hex
        root_span_id = uuid.uuid4().hex[:16]
        started = datetime.now(UTC)
        span_list = spans or [
            {
                "span_id": root_span_id,
                "parent_span_id": None,
                "service_name": self.settings.service_name,
                "operation_name": operation,
                "started_at": started.isoformat(),
                "duration_ms": duration_ms,
                "status": status,
                "attributes": {},
            }
        ]
        payload = {
            "traces": [
                {
                    "trace_id": trace_id,
                    "service_name": self.settings.service_name,
                    "root_operation": operation,
                    "started_at": started.isoformat(),
                    "duration_ms": duration_ms,
                    "status": status,
                    "attributes": {},
                    "spans": span_list,
                }
            ]
        }
        await self._post("/telemetry/traces", payload)
        return trace_id

    async def emit_deployment(self, version: str, notes: str | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        payload = {
            "deployments": [
                {
                    "service_name": self.settings.service_name,
                    "version": version,
                    "commit_sha": uuid.uuid4().hex[:8],
                    "status": "success",
                    "started_at": now,
                    "completed_at": now,
                    "metadata": {},
                    "notes": notes,
                }
            ]
        }
        await self._post("/telemetry/deployments", payload)

    async def _post(self, path: str, payload: dict[str, Any]) -> None:
        url = f"{self.settings.api_base_url}{path}"
        try:
            resp = await self._client.post(url, json=payload, headers=self._headers())
            if resp.status_code >= 400:
                logger.warning("telemetry emit failed %s %s", resp.status_code, resp.text[:200])
        except Exception as exc:  # noqa: BLE001 — simulator must keep running
            logger.warning("telemetry emit error: %s", exc)
