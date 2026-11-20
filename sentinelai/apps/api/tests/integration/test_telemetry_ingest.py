from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.conftest import login

TOKEN = "change-me-simulator-token"


@pytest.mark.asyncio
async def test_ingest_and_query_logs(client: AsyncClient) -> None:
    now = datetime.now(UTC).isoformat()
    resp = await client.post(
        "/api/v1/telemetry/logs",
        headers={"X-Simulator-Token": TOKEN},
        json={
            "logs": [
                {
                    "timestamp": now,
                    "service_name": "api-gateway",
                    "level": "ERROR",
                    "message": "Redis connection refused",
                    "trace_id": "abc123trace",
                    "correlation_id": "corr-1",
                    "attributes": {"injected": True},
                }
            ]
        },
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["accepted"] == 1

    # Reject without token
    bad = await client.post(
        "/api/v1/telemetry/logs",
        json={
            "logs": [
                {
                    "timestamp": now,
                    "service_name": "api-gateway",
                    "level": "INFO",
                    "message": "nope",
                }
            ]
        },
    )
    assert bad.status_code == 403

    user = await login(client, "viewer@example.com")
    search = await client.get(
        "/api/v1/telemetry/logs",
        headers={"Authorization": f"Bearer {user}"},
        params={"service": "api-gateway", "q": "Redis"},
    )
    assert search.status_code == 200
    body = search.json()
    assert body["total"] >= 1
    assert any("Redis" in item["message"] for item in body["items"])


@pytest.mark.asyncio
async def test_ingest_metrics_and_traces(client: AsyncClient) -> None:
    now = datetime.now(UTC).isoformat()
    metrics = await client.post(
        "/api/v1/telemetry/metrics",
        headers={"X-Simulator-Token": TOKEN},
        json={
            "metrics": [
                {
                    "timestamp": now,
                    "service_name": "order-service",
                    "metric_name": "http_error_rate",
                    "value": 0.42,
                    "labels": {"scenario": "http_500_spike"},
                }
            ]
        },
    )
    assert metrics.status_code == 202

    import uuid

    trace_id = f"trace-{uuid.uuid4().hex[:12]}"
    traces = await client.post(
        "/api/v1/telemetry/traces",
        headers={"X-Simulator-Token": TOKEN},
        json={
            "traces": [
                {
                    "trace_id": trace_id,
                    "service_name": "order-service",
                    "root_operation": "/api/orders",
                    "started_at": now,
                    "duration_ms": 1500,
                    "status": "error",
                    "spans": [
                        {
                            "span_id": "span-1",
                            "service_name": "order-service",
                            "operation_name": "/api/orders",
                            "started_at": now,
                            "duration_ms": 1500,
                            "status": "error",
                        }
                    ],
                }
            ]
        },
    )
    assert traces.status_code == 202

    user = await login(client, "viewer@example.com")
    detail = await client.get(
        f"/api/v1/telemetry/traces/{trace_id}",
        headers={"Authorization": f"Bearer {user}"},
    )
    assert detail.status_code == 200
    assert detail.json()["trace_id"] == trace_id
    assert len(detail.json()["spans"]) == 1
