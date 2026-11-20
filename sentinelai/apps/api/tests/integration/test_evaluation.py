import pytest
from httpx import AsyncClient

from tests.conftest import login


@pytest.mark.asyncio
async def test_evaluation_run_persists_measured_scores(client: AsyncClient) -> None:
    engineer = await login(client, "engineer@example.com")
    resp = await client.post(
        "/api/v1/evaluation/runs",
        headers={"Authorization": f"Bearer {engineer}"},
        json={
            "dataset_version": "v1",
            "provider": "deterministic",
            "model": "rules-v1",
        },
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["metrics"] is not None
    assert "root_cause_accuracy" in body["metrics"]
    assert "pass_rate" in body["metrics"]
    # Never fabricate remediation quality
    assert body["metrics"]["remediation_quality"] is None

    results = await client.get(
        f"/api/v1/evaluation/runs/{body['id']}/results",
        headers={"Authorization": f"Bearer {engineer}"},
    )
    assert results.status_code == 200
    assert len(results.json()["items"]) >= 1

    comparisons = await client.get(
        "/api/v1/evaluation/comparisons",
        headers={"Authorization": f"Bearer {engineer}"},
    )
    assert comparisons.status_code == 200
    assert "v1" in comparisons.json()["datasets"]
