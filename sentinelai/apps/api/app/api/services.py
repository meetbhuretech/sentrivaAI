from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.models.service import Service, ServiceDependency
from app.schemas.common import Page
from app.schemas.services import ServiceDependencyOut, ServiceOut

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=Page[ServiceOut])
async def list_services(db: DbSession, _user: CurrentUser) -> Page[ServiceOut]:
    result = await db.execute(select(Service).order_by(Service.name))
    items = list(result.scalars().all())
    return Page(items=items, page=1, page_size=len(items) or 1, total=len(items))


@router.get("/dependencies", response_model=list[ServiceDependencyOut])
async def list_dependencies(db: DbSession, _user: CurrentUser) -> list[ServiceDependencyOut]:
    deps = (await db.execute(select(ServiceDependency))).scalars().all()
    services = {
        s.id: s for s in (await db.execute(select(Service))).scalars().all()
    }
    out: list[ServiceDependencyOut] = []
    for dep in deps:
        out.append(
            ServiceDependencyOut(
                id=dep.id,
                source_service_id=dep.source_service_id,
                target_service_id=dep.target_service_id,
                dependency_type=dep.dependency_type,
                source_name=services[dep.source_service_id].name
                if dep.source_service_id in services
                else None,
                target_name=services[dep.target_service_id].name
                if dep.target_service_id in services
                else None,
            )
        )
    return out


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(service_id: UUID, db: DbSession, _user: CurrentUser) -> Service:
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar_one_or_none()
    if svc is None:
        raise AppError("NOT_FOUND", "Service not found", status_code=404)
    return svc


@router.get("/{service_id}/health")
async def service_health(service_id: UUID, db: DbSession, _user: CurrentUser) -> dict:
    result = await db.execute(select(Service).where(Service.id == service_id))
    svc = result.scalar_one_or_none()
    if svc is None:
        raise AppError("NOT_FOUND", "Service not found", status_code=404)
    return {
        "id": str(svc.id),
        "name": svc.name,
        "status": svc.status.value,
        "environment": svc.environment,
    }
