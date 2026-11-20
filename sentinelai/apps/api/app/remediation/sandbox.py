"""Sandboxed remediation executor.

ONLY allowlisted action types are executed.
Actions target the local simulator — never real production infrastructure.
Never executes arbitrary shell from LLM output.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sentinelai_contracts.enums import REMEDIATION_ACTION_ALLOWLIST

logger = logging.getLogger(__name__)


class SandboxExecutor:
    def __init__(self, service_urls: dict[str, str] | None = None) -> None:
        self.service_urls = service_urls or {
            "api-gateway": "http://127.0.0.1:8100",
            "user-service": "http://127.0.0.1:8101",
            "order-service": "http://127.0.0.1:8102",
            "payment-service": "http://127.0.0.1:8103",
        }

    async def execute(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        started = datetime.now(UTC)
        for action in actions:
            action_type = action.get("action_type")
            if action_type not in REMEDIATION_ACTION_ALLOWLIST:
                results.append(
                    {
                        "action_type": action_type,
                        "status": "rejected",
                        "reason": "action_type not in allowlist",
                    }
                )
                continue
            handler = getattr(self, f"_do_{action_type}", None)
            if handler is None:
                results.append(
                    {
                        "action_type": action_type,
                        "status": "unsupported",
                        "reason": "no sandbox handler",
                    }
                )
                continue
            try:
                outcome = await handler(action.get("parameters") or {})
                results.append({"action_type": action_type, "status": "succeeded", "result": outcome})
            except Exception as exc:  # noqa: BLE001
                logger.exception("sandbox action failed: %s", action_type)
                results.append(
                    {
                        "action_type": action_type,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
        succeeded = all(r["status"] == "succeeded" for r in results) if results else False
        return {
            "started_at": started.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "overall_status": "succeeded" if succeeded else "failed",
            "actions": results,
            "sandbox": True,
            "production_touch": False,
        }

    async def _do_disable_scenario(self, params: dict[str, Any]) -> dict[str, Any]:
        outcomes = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, base in self.service_urls.items():
                try:
                    resp = await client.post(f"{base}/scenarios/stop")
                    outcomes.append({"service": name, "status_code": resp.status_code})
                except Exception as exc:  # noqa: BLE001
                    outcomes.append({"service": name, "error": str(exc)})
        return {"stopped": outcomes}

    async def _do_clear_redis_connections(self, params: dict[str, Any]) -> dict[str, Any]:
        # Simulator proxy: stop redis failure scenario if active
        service = params.get("service", "api-gateway")
        base = self.service_urls.get(service, self.service_urls["api-gateway"])
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{base}/scenarios/stop")
        return {"service": service, "status_code": resp.status_code, "effect": "scenario_stopped"}

    async def _do_rollback_deployment(self, params: dict[str, Any]) -> dict[str, Any]:
        service = params.get("service", "api-gateway")
        base = self.service_urls.get(service, self.service_urls["api-gateway"])
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{base}/scenarios/stop")
        return {
            "service": service,
            "effect": "simulator_scenario_cleared",
            "note": "Sandbox rollback — no real cluster mutation",
        }

    async def _do_restart_service(self, params: dict[str, Any]) -> dict[str, Any]:
        service = params.get("service", "api-gateway")
        return {
            "service": service,
            "effect": "simulated_restart",
            "note": "No process kill in demo sandbox; recorded as successful soft restart",
        }

    async def _do_scale_connection_pool(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "service": params.get("service"),
            "new_size": params.get("size", 20),
            "effect": "simulated_pool_resize",
        }

    async def _do_flush_cache_namespace(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "namespace": params.get("namespace", "default"),
            "effect": "simulated_cache_flush",
        }
