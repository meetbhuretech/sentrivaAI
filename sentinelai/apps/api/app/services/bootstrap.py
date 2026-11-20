import logging

from sentinelai_contracts import Role, ServiceStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.service import Service, ServiceDependency
from app.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_SERVICES = [
    ("api-gateway", "API Gateway", "http://gateway:8100"),
    ("user-service", "User Service", "http://user-service:8101"),
    ("order-service", "Order Service", "http://order-service:8102"),
    ("payment-service", "Payment Simulation Service", "http://payment-service:8103"),
]

# source -> target, type
DEFAULT_DEPS = [
    ("api-gateway", "user-service", "http"),
    ("api-gateway", "order-service", "http"),
    ("order-service", "user-service", "http"),
    ("order-service", "payment-service", "http"),
    ("user-service", "postgres", "db"),
    ("order-service", "postgres", "db"),
    ("payment-service", "redis", "redis"),
    ("api-gateway", "redis", "redis"),
]


async def ensure_bootstrap_admin(db: AsyncSession) -> None:
    settings = get_settings()
    result = await db.execute(select(User).where(User.email == settings.bootstrap_admin_email))
    existing = result.scalar_one_or_none()
    if existing:
        return
    admin = User(
        email=settings.bootstrap_admin_email,
        password_hash=hash_password(settings.bootstrap_admin_password),
        full_name=settings.bootstrap_admin_name,
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    logger.info("Bootstrap admin created: %s", settings.bootstrap_admin_email)


async def ensure_default_services(db: AsyncSession) -> None:
    count = await db.scalar(select(func.count()).select_from(Service))
    if count and count > 0:
        return

    # Infrastructure placeholders for dependency map (not scraped as app services)
    infra = [
        ("postgres", "PostgreSQL", None),
        ("redis", "Redis", None),
    ]
    created: dict[str, Service] = {}
    for name, display, base_url in [*DEFAULT_SERVICES, *infra]:
        svc = Service(
            name=name,
            display_name=display,
            environment="local",
            base_url=base_url,
            status=ServiceStatus.HEALTHY if base_url else ServiceStatus.UNKNOWN,
            metadata_json={"kind": "app" if base_url else "infra"},
        )
        db.add(svc)
        created[name] = svc
    await db.flush()

    for source, target, dep_type in DEFAULT_DEPS:
        if source not in created or target not in created:
            continue
        db.add(
            ServiceDependency(
                source_service_id=created[source].id,
                target_service_id=created[target].id,
                dependency_type=dep_type,
            )
        )
    await db.flush()
    logger.info("Seeded default services and dependencies")
