from uuid import UUID

from sentinelai_contracts import ServiceStatus

from app.schemas.common import APIModel


class ServiceOut(APIModel):
    id: UUID
    name: str
    display_name: str
    environment: str
    base_url: str | None = None
    status: ServiceStatus


class ServiceDependencyOut(APIModel):
    id: UUID
    source_service_id: UUID
    target_service_id: UUID
    dependency_type: str
    source_name: str | None = None
    target_name: str | None = None
