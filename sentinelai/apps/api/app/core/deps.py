from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sentinelai_contracts import Role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_token, role_at_least
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise AppError("UNAUTHORIZED", "Missing bearer token", status_code=401)
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", status_code=401) from exc
    if payload.get("type") != "access":
        raise AppError("UNAUTHORIZED", "Access token required", status_code=401)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError("UNAUTHORIZED", "Invalid token subject", status_code=401)
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AppError("UNAUTHORIZED", "User not found or inactive", status_code=401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum: Role) -> Callable[..., User]:
    async def _checker(user: CurrentUser) -> User:
        if not role_at_least(user.role, minimum):
            raise AppError(
                "FORBIDDEN",
                f"Requires role {minimum.value} or higher",
                status_code=403,
            )
        return user

    return _checker


async def verify_simulator_token(
    x_simulator_token: Annotated[str | None, Header()] = None,
) -> None:
    settings = get_settings()
    if not x_simulator_token or x_simulator_token != settings.simulator_internal_token:
        raise AppError("FORBIDDEN", "Invalid simulator token", status_code=403)


def client_meta(request: Request) -> dict[str, str | None]:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
