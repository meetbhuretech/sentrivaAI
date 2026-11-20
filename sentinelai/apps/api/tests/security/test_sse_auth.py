import pytest
from httpx import AsyncClient

from tests.conftest import login


@pytest.mark.asyncio
async def test_overview_stream_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/overview/stream")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_overview_stream_rejects_garbage_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/overview/stream", params={"access_token": "not-a-jwt"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_overview_stream_accepts_access_token(client: AsyncClient) -> None:
    token = await login(client, "admin@example.com")
    # max_events=1 closes the stream so the ASGI test client does not hang.
    resp = await client.get(
        "/api/v1/overview/stream",
        params={"access_token": token, "max_events": 1},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert "event: overview" in resp.text
    assert "total_services" in resp.text
