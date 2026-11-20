from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import redact_secrets
from app.models.audit import AuditEvent


def _redact_details(details: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, str):
            redacted[key] = redact_secrets(value)
        elif isinstance(value, dict):
            redacted[key] = _redact_details(value)
        else:
            redacted[key] = value
    return redacted


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip=ip,
        user_agent=user_agent,
        details=_redact_details(details or {}),
    )
    db.add(event)
    await db.flush()
    return event
