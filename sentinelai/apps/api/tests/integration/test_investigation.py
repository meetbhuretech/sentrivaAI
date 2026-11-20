from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import login


@pytest.mark.asyncio
async def test_investigation_produces_grounded_rca(client: AsyncClient) -> None:
    # Seed spike metrics + error log
    now = datetime.now(UTC)
    await client.post(
        "/api/v1/telemetry/metrics",
        headers={"X-Simulator-Token": "change-me-simulator-token"},
        json={
            "metrics": [
                {
                    "timestamp": (now - timedelta(minutes=40)).isoformat(),
                    "service_name": "payment-service",
                    "metric_name": "http_error_rate",
                    "value": 0.01,
                    "labels": {},
                },
                {
                    "timestamp": now.isoformat(),
                    "service_name": "payment-service",
                    "metric_name": "http_error_rate",
                    "value": 0.5,
                    "labels": {},
                },
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
                    "service_name": "payment-service",
                    "level": "ERROR",
                    "message": "Redis connection refused during charge",
                    "trace_id": "paytrace001",
                    "attributes": {},
                }
            ]
        },
    )

    engineer = await login(client, "engineer@example.com")
    # Detect incident
    det = await client.post(
        "/api/v1/alerts/evaluate",
        headers={"Authorization": f"Bearer {engineer}"},
    )
    assert det.status_code == 200
    assert det.json()["incident_ids"], "expected an incident from detection"

    incident_id = det.json()["incident_ids"][0]
    inv = await client.post(
        f"/api/v1/incidents/{incident_id}/investigate",
        headers={"Authorization": f"Bearer {engineer}"},
        json={"provider": "deterministic", "model": "rules-v1"},
    )
    assert inv.status_code == 202, inv.text
    body = inv.json()
    assert body["provider"] == "deterministic"
    assert body["status"] == "awaiting_approval"
    assert body["rca"] is not None
    assert "probable_root_cause" in body["rca"]
    assert "confidence" in body["rca"]
    assert "confidence_components" in body["rca"]
    assert body["rca"]["supporting_evidence"] is not None
    assert "[ESTIMATE]" in body["rca"]["business_impact_estimate"]

    evidence = await client.get(
        f"/api/v1/investigations/{body['id']}/evidence",
        headers={"Authorization": f"Bearer {engineer}"},
    )
    assert evidence.status_code == 200
    ev = evidence.json()
    assert len(ev["findings"]) >= 4
    assert len(ev["tool_calls"]) >= 1

    timeline = await client.get(
        f"/api/v1/investigations/{body['id']}/timeline",
        headers={"Authorization": f"Bearer {engineer}"},
    )
    assert timeline.status_code == 200
    steps = [e["step"] for e in timeline.json()["events"]]
    assert "log_investigation" in steps
    assert "awaiting_approval" in steps
