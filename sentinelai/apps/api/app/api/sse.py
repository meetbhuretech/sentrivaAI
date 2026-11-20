"""SSE helpers — EventSource cannot set Authorization headers, so streams
accept `?access_token=` in addition to the normal Bearer dependency path.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import Query
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.errors import AppError
from app.core.security import decode_token
from app.models.user import User


async def user_from_access_token(access_token: str | None = Query(default=None)) -> User:
    if not access_token:
        raise AppError(
            "UNAUTHORIZED",
            "SSE requires access_token query parameter (EventSource cannot send Authorization)",
            status_code=401,
        )
    try:
        payload = decode_token(access_token)
    except ValueError as exc:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", status_code=401) from exc
    if payload.get("type") != "access":
        raise AppError("UNAUTHORIZED", "Access token required", status_code=401)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError("UNAUTHORIZED", "Invalid token subject", status_code=401)
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.id == UUID(user_id)))
        ).scalar_one_or_none()
        if user is None or not user.is_active:
            raise AppError("UNAUTHORIZED", "User not found or inactive", status_code=401)
        return user


def sse_pack(event: str, data: Any) -> str:
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


async def heartbeat(interval: float = 15.0) -> AsyncIterator[str]:
    """Unused generator kept for documentation; callers inline sleep."""
    yield sse_pack("ping", {"ok": True})
