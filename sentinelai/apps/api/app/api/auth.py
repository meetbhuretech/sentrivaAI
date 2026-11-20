from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sentinelai_contracts import Role
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, client_meta, get_current_user
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])
_optional_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, request: Request, db: DbSession) -> TokenPair:
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError("UNAUTHORIZED", "Invalid email or password", status_code=401)
    if not user.is_active:
        raise AppError("FORBIDDEN", "User is inactive", status_code=403)
    meta = client_meta(request)
    await write_audit(
        db,
        action="auth.login",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token)
    except ValueError as exc:
        raise AppError("UNAUTHORIZED", "Invalid refresh token", status_code=401) from exc
    if payload.get("type") != "refresh":
        raise AppError("UNAUTHORIZED", "Refresh token required", status_code=401)
    result = await db.execute(select(User).where(User.id == UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AppError("UNAUTHORIZED", "User not found or inactive", status_code=401)
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, request: Request, db: DbSession) -> User:
    """First user may self-register as admin; thereafter only admins can register users."""
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    meta = client_meta(request)
    actor: User | None = None

    if total > 0:
        credentials: HTTPAuthorizationCredentials | None = await _optional_bearer(request)
        if credentials is None:
            raise AppError("UNAUTHORIZED", "Admin authentication required", status_code=401)
        actor = await get_current_user(db, credentials)
        if actor.role != Role.ADMIN:
            raise AppError("FORBIDDEN", "Only admins can register users", status_code=403)

    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise AppError("CONFLICT", "Email already registered", status_code=409)

    role = Role.ADMIN if total == 0 else body.role
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await write_audit(
        db,
        action="auth.register",
        actor_user_id=actor.id if actor else user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        details={"email": user.email, "role": user.role.value},
    )
    return user
