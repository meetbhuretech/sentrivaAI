"""Explicit investigation state machine with checkpointing and budgets."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sentinelai_contracts import IncidentStatus, InvestigationStatus, RemediationStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.confidence import compute_confidence
from app.agents.specialists import (
    build_hypotheses,
    deployment_investigation_agent,
    log_investigation_agent,
    metrics_investigation_agent,
    trace_investigation_agent,
)
from app.agents.state import (
    EvidenceRef,
    InvestigationState,
    InvestigationStep,
    RootCauseModel,
)
from app.agents.tools import InvestigationTools
from app.ai.registry import resolve_provider
from app.core.config import get_settings
from app.models.incident import Incident
from app.models.investigation import AgentFinding, Hypothesis, Investigation, InvestigationCheckpoint
from app.models.remediation import RemediationPlan
from app.models.service import Deployment
from app.models.telemetry import MetricSample, TelemetryLog, TelemetrySpan, TelemetryTrace

logger = logging.getLogger(__name__)

STEP_TO_STATUS = {
    InvestigationStep.PENDING: InvestigationStatus.PENDING,
    InvestigationStep.INITIALIZING: InvestigationStatus.INITIALIZING,
    InvestigationStep.GATHERING_CONTEXT: InvestigationStatus.GATHERING_CONTEXT,
    InvestigationStep.LOG_INVESTIGATION: InvestigationStatus.LOG_INVESTIGATION,
    InvestigationStep.METRICS_INVESTIGATION: InvestigationStatus.METRICS_INVESTIGATION,
    InvestigationStep.TRACE_INVESTIGATION: InvestigationStatus.TRACE_INVESTIGATION,
    InvestigationStep.DEPLOYMENT_INVESTIGATION: InvestigationStatus.DEPLOYMENT_INVESTIGATION,
    InvestigationStep.ROOT_CAUSE_ANALYSIS: InvestigationStatus.ROOT_CAUSE_ANALYSIS,
    InvestigationStep.EVIDENCE_EVALUATION: InvestigationStatus.EVIDENCE_EVALUATION,
    InvestigationStep.REMEDIATION_PROPOSAL: InvestigationStatus.REMEDIATION_PROPOSAL,
    InvestigationStep.AWAITING_APPROVAL: InvestigationStatus.AWAITING_APPROVAL,
    InvestigationStep.COMPLETED: InvestigationStatus.COMPLETED,
    InvestigationStep.FAILED: InvestigationStatus.FAILED,
    InvestigationStep.CANCELLED: InvestigationStatus.CANCELLED,
    InvestigationStep.TIMED_OUT: InvestigationStatus.TIMED_OUT,
}


class InvestigationOrchestrator:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def start(
        self,
        incident_id: UUID,
        *,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> Investigation:
        incident = (
            await self.db.execute(select(Incident).where(Incident.id == incident_id))
        ).scalar_one_or_none()
        if incident is None:
            raise ValueError("Incident not found")

        provider, effective = await resolve_provider(provider_name)
        model_name = model or self.settings.default_ai_model
        if effective == "deterministic":
            model_name = "rules-v1"

        now = datetime.now(UTC)
        inv = Investigation(
            id=uuid4(),
            incident_id=incident_id,
            status=InvestigationStatus.PENDING,
            current_step=InvestigationStep.PENDING.value,
            provider=effective,
            model=model_name,
            prompt_version="v1",
            state={},
            token_usage={},
            estimated_cost_usd=Decimal("0"),
            started_at=now,
            deadline_at=now + timedelta(seconds=self.settings.investigation_timeout_seconds),
        )
        self.db.add(inv)
        await self.db.flush()

        state = InvestigationState(
            investigation_id=inv.id,
            incident_id=incident_id,
            status=InvestigationStatus.PENDING,
            current_step=InvestigationStep.PENDING,
            provider=effective,
            model=model_name,
            started_at=now,
            updated_at=now,
            deadline_at=inv.deadline_at,
            max_tool_calls=self.settings.max_tool_calls,
        )
        await self._checkpoint(inv, state)

        incident.status = IncidentStatus.INVESTIGATING
        await self.db.flush()

        try:
            await self._run(inv, state, provider)
        except Exception as exc:  # noqa: BLE001
            logger.exception("investigation failed")
            state.status = InvestigationStatus.FAILED
            state.current_step = InvestigationStep.FAILED
            state.errors.append(str(exc))
            state.completed_at = datetime.now(UTC)
            inv.error_message = str(exc)
            await self._persist(inv, state)

        return inv

    async def _run(self, inv: Investigation, state: InvestigationState, provider) -> None:
        tools = InvestigationTools(self.db, max_calls=state.max_tool_calls)

        async def transition(step: InvestigationStep) -> None:
            if state.deadline_at and datetime.now(UTC) > state.deadline_at:
                raise TimeoutError("Investigation deadline exceeded")
            state.current_step = step
            state.status = STEP_TO_STATUS[step]
            state.updated_at = datetime.now(UTC)
            await self._checkpoint(inv, state)

        await transition(InvestigationStep.INITIALIZING)
        incident = await tools.load_incident(state.incident_id)
        assert incident is not None
        services = list(incident.service_names or [])
        alerts = await tools.get_incident_alerts(state.incident_id)
        health = await tools.get_service_health()
        state.context = {
            "incident": {
                "id": str(incident.id),
                "title": incident.title,
                "severity": incident.severity.value,
                "summary": incident.summary,
                "service_names": services,
            },
            "alerts": alerts,
            "health": health,
        }

        await transition(InvestigationStep.GATHERING_CONTEXT)

        await transition(InvestigationStep.LOG_INVESTIGATION)
        state.log_findings = [
            await log_investigation_agent(
                tools, services=services, provider=provider, model=state.model
            )
        ]
        await self._store_finding(inv.id, state.log_findings[0])

        await transition(InvestigationStep.METRICS_INVESTIGATION)
        state.metrics_findings = [
            await metrics_investigation_agent(
                tools, services=services, provider=provider, model=state.model
            )
        ]
        await self._store_finding(inv.id, state.metrics_findings[0])

        await transition(InvestigationStep.TRACE_INVESTIGATION)
        state.trace_findings = [
            await trace_investigation_agent(
                tools, services=services, provider=provider, model=state.model
            )
        ]
        await self._store_finding(inv.id, state.trace_findings[0])

        await transition(InvestigationStep.DEPLOYMENT_INVESTIGATION)
        state.deployment_findings = [
            await deployment_investigation_agent(
                tools, services=services, provider=provider, model=state.model
            )
        ]
        await self._store_finding(inv.id, state.deployment_findings[0])

        await transition(InvestigationStep.ROOT_CAUSE_ANALYSIS)
        findings = (
            state.log_findings
            + state.metrics_findings
            + state.trace_findings
            + state.deployment_findings
        )
        state.hypotheses = build_hypotheses(
            findings=findings, alerts=alerts, services=services
        )
        for i, h in enumerate(state.hypotheses, start=1):
            self.db.add(
                Hypothesis(
                    investigation_id=inv.id,
                    statement=h.statement,
                    rank=i,
                    confidence=h.confidence,
                    confidence_components={},
                    evidence_refs=[e.model_dump() for e in h.evidence_refs],
                )
            )
        await self.db.flush()

        await transition(InvestigationStep.EVIDENCE_EVALUATION)
        grounded: list[EvidenceRef] = []
        for h in state.hypotheses:
            valid_refs: list[EvidenceRef] = []
            notes = []
            for ref in h.evidence_refs:
                ok = await self._evidence_exists(ref)
                if ok:
                    valid_refs.append(ref)
                    grounded.append(ref)
                else:
                    notes.append(f"missing {ref.kind}:{ref.id}")
            h.grounded = len(valid_refs) == len(h.evidence_refs) and len(valid_refs) > 0
            h.evidence_refs = valid_refs
            h.evaluation_notes = "; ".join(notes) if notes else "all refs verified"
            state.evaluated_hypotheses.append(h)

        top = state.evaluated_hypotheses[0] if state.evaluated_hypotheses else state.hypotheses[0]
        # Signal strength from alert severities
        sev_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3, "info": 0.1}
        signal = max((sev_map.get(a.get("severity", "info"), 0.2) for a in alerts), default=0.2)
        # Temporal alignment: deployment within window boosts score
        temporal = 0.7 if state.deployment_findings and state.deployment_findings[0].evidence_refs else 0.3
        confidence, components = compute_confidence(
            top_hypothesis=top,
            findings=findings,
            grounded_refs=grounded,
            signal_strength=signal,
            temporal_alignment=temporal,
        )
        alternatives = state.evaluated_hypotheses[1:] if len(state.evaluated_hypotheses) > 1 else []
        state.rca = RootCauseModel(
            summary=incident.summary or incident.title,
            probable_root_cause=top.statement,
            confidence=confidence,
            confidence_components=components,
            supporting_evidence=top.evidence_refs,
            alternative_hypotheses=alternatives,
            affected_services=services,
            business_impact_estimate=(
                "[ESTIMATE] Possible customer-facing errors/latency; "
                "revenue impact not measured in this demo."
            ),
            recommended_actions=[
                "Confirm firing alerts in Remediation Center",
                "Review supporting evidence (logs/metrics/traces)",
                "Approve sandboxed remediation if appropriate",
            ],
            source="hybrid" if provider.name != "deterministic" else "deterministic",
        )

        await transition(InvestigationStep.REMEDIATION_PROPOSAL)
        plan = await self._propose_remediation(inv, incident, state)
        state.remediation_plan_id = plan.id

        state.tool_calls = tools.calls
        state.tool_calls_used = len(tools.calls)
        await transition(InvestigationStep.AWAITING_APPROVAL)
        state.completed_at = datetime.now(UTC)
        # Awaiting approval is the terminal autonomous state
        await self._persist(inv, state)

    async def _propose_remediation(
        self, inv: Investigation, incident: Incident, state: InvestigationState
    ) -> RemediationPlan:
        actions = []
        cause = (state.rca.probable_root_cause if state.rca else "").lower()
        target = incident.service_names[0] if incident.service_names else "api-gateway"
        if "redis" in cause:
            actions.append(
                {
                    "action_type": "clear_redis_connections",
                    "parameters": {"service": target},
                    "command_preview": "sandbox: reset redis connection pool on target service",
                }
            )
        if "deploy" in cause or "regression" in cause:
            actions.append(
                {
                    "action_type": "rollback_deployment",
                    "parameters": {"service": target},
                    "command_preview": "sandbox: rollback to previous simulator version",
                }
            )
        if "error_rate" in cause or not actions:
            actions.append(
                {
                    "action_type": "disable_scenario",
                    "parameters": {"scenario": "auto"},
                    "command_preview": "sandbox: stop active failure scenario on simulators",
                }
            )
        plan = RemediationPlan(
            investigation_id=inv.id,
            incident_id=incident.id,
            status=RemediationStatus.PROPOSED,
            problem_summary=state.rca.summary if state.rca else incident.title,
            rationale=state.rca.probable_root_cause if state.rca else "Correlated alerts",
            actions=actions,
            risks="Sandbox-only execution; may not fully restore if root cause is misidentified.",
            rollback_steps=["Re-run detection", "Re-enable scenario if testing"],
            expected_impact="[ESTIMATE] Error rate / latency may decrease if action matches cause.",
        )
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def _evidence_exists(self, ref: EvidenceRef) -> bool:
        try:
            uid = UUID(ref.id)
        except ValueError:
            # trace_id style
            if ref.kind == "trace":
                row = (
                    await self.db.execute(
                        select(TelemetryTrace).where(TelemetryTrace.trace_id == ref.id)
                    )
                ).scalar_one_or_none()
                return row is not None
            return False
        model_map = {
            "log": TelemetryLog,
            "metric": MetricSample,
            "span": TelemetrySpan,
            "trace": TelemetryTrace,
            "deployment": Deployment,
            "alert": __import__("app.models.incident", fromlist=["Alert"]).Alert,
        }
        model = model_map.get(ref.kind)
        if not model:
            return False
        row = (await self.db.execute(select(model).where(model.id == uid))).scalar_one_or_none()
        return row is not None

    async def _store_finding(self, investigation_id: UUID, finding) -> None:
        self.db.add(
            AgentFinding(
                investigation_id=investigation_id,
                agent_name=finding.agent_name,
                summary=finding.summary,
                details=finding.details,
                evidence_refs=[e.model_dump() for e in finding.evidence_refs],
                source=finding.source,
            )
        )
        await self.db.flush()

    async def _checkpoint(self, inv: Investigation, state: InvestigationState) -> None:
        inv.status = state.status
        inv.current_step = state.current_step.value
        inv.state = state.model_dump(mode="json")
        if state.rca:
            inv.rca = state.rca.model_dump(mode="json")
        self.db.add(
            InvestigationCheckpoint(
                investigation_id=inv.id,
                step=state.current_step.value,
                state=state.model_dump(mode="json"),
            )
        )
        await self.db.flush()

    async def _persist(self, inv: Investigation, state: InvestigationState) -> None:
        inv.status = state.status
        inv.current_step = state.current_step.value
        inv.state = state.model_dump(mode="json")
        inv.rca = state.rca.model_dump(mode="json") if state.rca else None
        inv.token_usage = state.token_usage
        inv.estimated_cost_usd = Decimal(str(round(state.estimated_cost_usd, 6)))
        inv.completed_at = state.completed_at
        if state.errors:
            inv.error_message = "; ".join(state.errors)
        await self.db.flush()
