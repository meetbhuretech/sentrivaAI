"""Lightweight MCP-style tool endpoint.

Exposes tools with explicit permission scopes:
- scope=investigate (read-only)
- scope=remediate (permissioned; still requires human approval for execution)

This demonstrates standardized tool interoperability without depending on
LangChain. Clients call JSON-RPC-like methods over HTTP.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field
from sentinelai_contracts.enums import REMEDIATION_ACTION_ALLOWLIST
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import InvestigationTools
from app.core.database import AsyncSessionLocal
from app.core.deps import verify_simulator_token
from app.core.errors import AppError
from app.remediation.sandbox import SandboxExecutor

router = APIRouter(prefix="/mcp", tags=["mcp"])

READ_ONLY_TOOLS = {
    "search_logs",
    "query_metrics",
    "inspect_trace",
    "get_service_health",
    "get_deployment_history",
    "create_incident_report",
}

REMEDIATION_TOOLS = {
    "generate_remediation_plan",
    "execute_sandbox_action",  # still sandbox-only; approval enforced at API layer for plans
}


class MCPRequest(BaseModel):
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    id: str | int | None = None


class MCPResponse(BaseModel):
    id: str | int | None = None
    result: Any = None
    error: dict[str, Any] | None = None


@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    return {
        "read_only": sorted(READ_ONLY_TOOLS),
        "remediation": sorted(REMEDIATION_TOOLS),
        "remediation_action_allowlist": sorted(REMEDIATION_ACTION_ALLOWLIST),
        "notes": (
            "Remediation tools are sandbox-scoped. "
            "Plan execution still requires engineer approval via /remediations/{id}/approve."
        ),
    }


@router.post("/call", response_model=MCPResponse)
async def mcp_call(
    body: MCPRequest,
    x_mcp_scope: str = Header(default="investigate"),
    x_simulator_token: str | None = Header(default=None),
) -> MCPResponse:
    """Dispatch a tool call. Investigate scope is default; remediate requires scope header."""
    # Reuse simulator token as a simple shared secret for machine clients in demo.
    try:
        await verify_simulator_token(x_simulator_token)
    except AppError as exc:
        return MCPResponse(id=body.id, error={"code": exc.code, "message": exc.message})

    tool = body.method
    if tool in READ_ONLY_TOOLS:
        if x_mcp_scope not in {"investigate", "remediate", "admin"}:
            return MCPResponse(
                id=body.id,
                error={"code": "FORBIDDEN", "message": "investigate scope required"},
            )
    elif tool in REMEDIATION_TOOLS:
        if x_mcp_scope not in {"remediate", "admin"}:
            return MCPResponse(
                id=body.id,
                error={"code": "FORBIDDEN", "message": "remediate scope required"},
            )
    else:
        return MCPResponse(
            id=body.id,
            error={"code": "METHOD_NOT_FOUND", "message": f"Unknown tool {tool}"},
        )

    async with AsyncSessionLocal() as db:
        try:
            result = await _dispatch(db, tool, body.params)
            await db.commit()
            return MCPResponse(id=body.id, result=result)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            return MCPResponse(id=body.id, error={"code": "TOOL_ERROR", "message": str(exc)})


async def _dispatch(db: AsyncSession, tool: str, params: dict[str, Any]) -> Any:
    tools = InvestigationTools(db)
    if tool == "search_logs":
        return await tools.search_logs(
            service_name=params.get("service_name"),
            level=params.get("level", "ERROR"),
            minutes=int(params.get("minutes", 30)),
            limit=int(params.get("limit", 50)),
        )
    if tool == "query_metrics":
        return await tools.query_metrics(
            service_name=params.get("service_name"),
            metric_name=params.get("metric_name"),
            minutes=int(params.get("minutes", 30)),
            limit=int(params.get("limit", 100)),
        )
    if tool == "inspect_trace":
        return await tools.inspect_trace(str(params["trace_id"]))
    if tool == "get_service_health":
        return await tools.get_service_health(params.get("service_name"))
    if tool == "get_deployment_history":
        return await tools.get_deployment_history(
            service_name=params.get("service_name"),
            minutes=int(params.get("minutes", 180)),
        )
    if tool == "create_incident_report":
        incident_id = UUID(params["incident_id"])
        incident = await tools.load_incident(incident_id)
        if not incident:
            raise ValueError("incident not found")
        alerts = await tools.get_incident_alerts(incident_id)
        return {
            "incident_id": str(incident.id),
            "title": incident.title,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "services": incident.service_names,
            "alerts": alerts,
            "generated": True,
        }
    if tool == "generate_remediation_plan":
        # Proposal only — does not execute
        return {
            "status": "proposed",
            "actions": [
                {
                    "action_type": "disable_scenario",
                    "parameters": {"scenario": "auto"},
                    "command_preview": "sandbox: stop active failure scenario",
                }
            ],
            "note": "Submit via investigation workflow; execution requires human approval",
            "allowlist": sorted(REMEDIATION_ACTION_ALLOWLIST),
        }
    if tool == "execute_sandbox_action":
        action_type = params.get("action_type")
        if action_type not in REMEDIATION_ACTION_ALLOWLIST:
            raise ValueError("action not allowlisted")
        # Direct sandbox call for demo interoperability — production path uses approval API
        executor = SandboxExecutor()
        return await executor.execute(
            [{"action_type": action_type, "parameters": params.get("parameters") or {}}]
        )
    raise ValueError(f"Unhandled tool {tool}")
