import pytest
from httpx import AsyncClient

from tests.conftest import login


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient) -> None:
    token = await login(client, "admin@example.com")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password-here"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_overview_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/overview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_overview_from_db(client: AsyncClient) -> None:
    token = await login(client, "viewer@example.com")
    resp = await client.get("/api/v1/overview", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_services"] >= 4
    assert "severity_distribution" in body
    assert body["request_rate"] >= 0.0  # computed from DB samples (0 if none)


@pytest.mark.asyncio
async def test_list_services(client: AsyncClient) -> None:
    token = await login(client, "viewer@example.com")
    resp = await client.get("/api/v1/services", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()["items"]}
    assert "api-gateway" in names
    assert "payment-service" in names
