import asyncio
import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sentinelai_contracts import Role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMeAdmin123!")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://sentinelai:sentinelai@localhost:5432/sentinelai",
    ),
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    os.getenv(
        "TEST_DATABASE_URL_SYNC",
        "postgresql://sentinelai:sentinelai@localhost:5432/sentinelai",
    ),
)

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import create_app
from app.models.user import User
from app.services.bootstrap import ensure_default_services

get_settings.cache_clear()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _seed(session: AsyncSession) -> None:
    await ensure_default_services(session)
    for email, role, name in [
        ("admin@example.com", Role.ADMIN, "Admin"),
        ("engineer@example.com", Role.ENGINEER, "Engineer"),
        ("viewer@example.com", Role.VIEWER, "Viewer"),
    ]:
        found = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not found:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password("ChangeMeAdmin123!"),
                    full_name=name,
                    role=role,
                    is_active=True,
                )
            )
    await session.commit()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Use create_all for tests. Prefer a dedicated TEST_DATABASE_URL in CI.

    Avoids leaving alembic_version pointing at a schema that was drop_all'd.
    """
    settings = get_settings()
    eng = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def login(client: AsyncClient, email: str, password: str = "ChangeMeAdmin123!") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
