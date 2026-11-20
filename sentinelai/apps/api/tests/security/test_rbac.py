import pytest
from httpx import AsyncClient
from sentinelai_contracts import IncidentStatus, Severity

from tests.conftest import login


@pytest.mark.asyncio
async def test_viewer_cannot_update_incident(client: AsyncClient) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.models.incident import Incident

    admin = await login(client, "admin@example.com")
    viewer = await login(client, "viewer@example.com")
    fake_id = str(uuid4())
    resp = await client.patch(
        f"/api/v1/incidents/{fake_id}",
        headers={"Authorization": f"Bearer {viewer}"},
        json={"status": "resolved"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    engineer = await login(client, "engineer@example.com")
    resp2 = await client.patch(
        f"/api/v1/incidents/{fake_id}",
        headers={"Authorization": f"Bearer {engineer}"},
        json={"status": "resolved"},
    )
    assert resp2.status_code == 404

    eng = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(eng, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        incident = Incident(
            title="Test incident",
            status=IncidentStatus.OPEN,
            severity=Severity.HIGH,
            service_names=["api-gateway"],
            detected_at=datetime.now(UTC),
            summary="seeded for rbac test",
        )
        session.add(incident)
        await session.commit()
        incident_id = str(incident.id)
    await eng.dispose()

    resp3 = await client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {engineer}"},
        json={"status": "resolved"},
    )
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "resolved"
    assert resp3.json()["mttr_seconds"] is not None

    resp4 = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {viewer}"})
    assert resp4.status_code == 403

    resp5 = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {admin}"})
    assert resp5.status_code == 200
