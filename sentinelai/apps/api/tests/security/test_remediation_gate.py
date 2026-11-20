from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sentinelai_contracts.enums import REMEDIATION_ACTION_ALLOWLIST

from tests.conftest import login


async def _investigate(client: AsyncClient, token: str) -> dict:
    now = datetime.now(UTC)
    await client.post(
        "/api/v1/telemetry/metrics",
        headers={"X-Simulator-Token": "change-me-simulator-token"},
        json={
            "metrics": [
                {
                    "timestamp": now.isoformat(),
                    "service_name": "user-service",
                    "metric_name": "http_error_rate",
                    "value": 0.6,
                    "labels": {},
                }
            ]
        },
    )
    await client.post(
        "/api/v1/telemetry/logs",
        headers={"X-Simulator-Token": "change-me-simulator-token"},
        json={
            "logs": [
                {
                    "timestamp": now.isoformat(),
                    "service_name": "user-service",
                    "level": "ERROR",
                    "message": "dependency timeout calling payment-service",
                    "attributes": {},
                }
            ]
        },
    )
    det = await client.post("/api/v1/alerts/evaluate", headers={"Authorization": f"Bearer {token}"})
    assert det.status_code == 200
    incident_id = det.json()["incident_ids"][0]
    inv = await client.post(
        f"/api/v1/incidents/{incident_id}/investigate",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider": "deterministic"},
    )
    assert inv.status_code == 202, inv.text
    return inv.json()


@pytest.mark.asyncio
async def test_remediation_requires_approval_and_viewer_blocked(client: AsyncClient) -> None:
    engineer = await login(client, "engineer@example.com")
    viewer = await login(client, "viewer@example.com")
    await _investigate(client, engineer)

    plans = await client.get("/api/v1/remediations", headers={"Authorization": f"Bearer {engineer}"})
    assert plans.status_code == 200
    assert plans.json()["total"] >= 1
    plan = plans.json()["items"][0]
    assert plan["status"] == "proposed"
    for action in plan["actions"]:
        assert action["action_type"] in REMEDIATION_ACTION_ALLOWLIST

    # Viewer cannot approve
    denied = await client.post(
        f"/api/v1/remediations/{plan['id']}/approve",
        headers={"Authorization": f"Bearer {viewer}"},
    )
    assert denied.status_code == 403

    # Engineer approves → sandbox execute
    approved = await client.post(
        f"/api/v1/remediations/{plan['id']}/approve",
        headers={"Authorization": f"Bearer {engineer}"},
        json={"reason": "demo approval"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] in {"succeeded", "failed"}

    execution = await client.get(
        f"/api/v1/remediations/{plan['id']}/execution",
        headers={"Authorization": f"Bearer {engineer}"},
    )
    assert execution.status_code == 200
    assert execution.json()["result"]["sandbox"] is True
    assert execution.json()["result"]["production_touch"] is False


@pytest.mark.asyncio
async def test_mcp_scope_separation(client: AsyncClient) -> None:
    tools = await client.get(
        "/api/v1/mcp/tools",
        headers={"X-Simulator-Token": "change-me-simulator-token"},
    )
    # list tools is open via router but call requires token — tools endpoint has no auth
    # Actually tools endpoint has no token check - OK for discovery
    assert tools.status_code == 200
    assert "search_logs" in tools.json()["read_only"]
    assert "execute_sandbox_action" in tools.json()["remediation"]

    # remediate tool denied under investigate scope
    denied = await client.post(
        "/api/v1/mcp/call",
        headers={
            "X-Simulator-Token": "change-me-simulator-token",
            "X-MCP-Scope": "investigate",
        },
        json={
            "method": "execute_sandbox_action",
            "params": {"action_type": "disable_scenario", "parameters": {}},
            "id": 1,
        },
    )
    assert denied.status_code == 200
    assert denied.json()["error"]["code"] == "FORBIDDEN"

    # read tool allowed
    ok = await client.post(
        "/api/v1/mcp/call",
        headers={
            "X-Simulator-Token": "change-me-simulator-token",
            "X-MCP-Scope": "investigate",
        },
        json={"method": "get_service_health", "params": {}, "id": 2},
    )
    assert ok.status_code == 200
    assert ok.json()["error"] is None
    assert isinstance(ok.json()["result"], list)
