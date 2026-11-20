# Agent State Machine

## Overview

Investigation is an explicit finite-state machine in Python. State is typed (`InvestigationState`), checkpointed to PostgreSQL after every transition, and resumable after process restart.

No LangChain / LangGraph dependency.

## States

```
PENDING
  → INITIALIZING
  → GATHERING_CONTEXT
  → LOG_INVESTIGATION
  → METRICS_INVESTIGATION
  → TRACE_INVESTIGATION
  → DEPLOYMENT_INVESTIGATION
  → ROOT_CAUSE_ANALYSIS
  → EVIDENCE_EVALUATION
  → REMEDIATION_PROPOSAL
  → AWAITING_APPROVAL          # human gate
  → COMPLETED | FAILED | CANCELLED | TIMED_OUT
```

Parallel fan-out (optional path after `GATHERING_CONTEXT`):

```
GATHERING_CONTEXT
  → PARALLEL_AGENTS (log | metrics | trace | deployment)
  → MERGE_FINDINGS
  → ROOT_CAUSE_ANALYSIS
  → ...
```

v0.1 implements sequential agents first; parallel is a documented extension with the same typed findings merge.

## Typed State (conceptual)

```python
class InvestigationState(BaseModel):
    investigation_id: UUID
    incident_id: UUID
    status: InvestigationStatus
    current_step: InvestigationStep
    provider: str
    model: str
    prompt_version: str

    context: IncidentContext
    log_findings: list[AgentFinding]
    metrics_findings: list[AgentFinding]
    trace_findings: list[AgentFinding]
    deployment_findings: list[AgentFinding]

    hypotheses: list[Hypothesis]
    evaluated_hypotheses: list[EvaluatedHypothesis]
    rca: RootCauseAnalysis | None
    remediation_plan_id: UUID | None

    tool_calls: list[ToolCallRecord]
    token_usage: TokenUsage
    estimated_cost_usd: float
    errors: list[str]
    checkpoints: list[CheckpointMeta]

    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    deadline_at: datetime
```

## Transition Rules

| From | To | Guard |
|------|-----|-------|
| PENDING | INITIALIZING | Investigation created |
| INITIALIZING | GATHERING_CONTEXT | Incident + services loaded |
| GATHERING_CONTEXT | LOG_INVESTIGATION | Context complete |
| LOG_INVESTIGATION | METRICS_INVESTIGATION | Log agent done or skipped |
| METRICS_INVESTIGATION | TRACE_INVESTIGATION | Metrics agent done or skipped |
| TRACE_INVESTIGATION | DEPLOYMENT_INVESTIGATION | Trace agent done or skipped |
| DEPLOYMENT_INVESTIGATION | ROOT_CAUSE_ANALYSIS | Deployment agent done or skipped |
| ROOT_CAUSE_ANALYSIS | EVIDENCE_EVALUATION | ≥1 hypothesis produced |
| EVIDENCE_EVALUATION | REMEDIATION_PROPOSAL | Evaluator finished |
| REMEDIATION_PROPOSAL | AWAITING_APPROVAL | Plan persisted |
| AWAITING_APPROVAL | COMPLETED | Approved/rejected/cancelled recorded |
| * | FAILED | Unrecoverable error after retries |
| * | TIMED_OUT | `deadline_at` exceeded |
| * | CANCELLED | Operator cancel |

## Bounds & Budgets

| Limit | Default | Configurable |
|-------|---------|--------------|
| Investigation timeout | 120s | yes |
| Per-agent timeout | 30s | yes |
| Max retries per agent | 2 | yes |
| Max tool calls total | 40 | yes |
| Max tokens (input+output) | 80_000 | yes |
| Estimated cost ceiling (USD) | 1.00 | yes |

Exceeding any budget transitions to `FAILED` with reason, or falls back to deterministic analysis if the step allows.

## Deterministic Fallback

When LLM is unavailable or returns invalid structured output:

1. Log agent: regex/error-code frequency over recent logs.
2. Metrics agent: threshold comparisons vs baselines.
3. Trace agent: slowest spans + error spans by duration.
4. Deployment agent: deployments in incident window ± lookback.
5. Root cause: rule-based scoring of correlated signals.
6. Evidence evaluator: verify each evidence_ref exists in DB.

Fallback results are labeled `source: deterministic` and never claim LLM authorship.

## Confidence Score Calculation

Documented formula (implemented in code, not marketing copy):

```
confidence = clamp(
  0.35 * evidence_coverage      # fraction of claims with valid refs
+ 0.25 * cross_agent_agreement  # fraction of agents supporting top cause
+ 0.20 * signal_strength        # normalized severity of matching alerts
+ 0.20 * temporal_alignment     # deployment/change proximity score
, 0.0, 1.0)
```

Each component is stored on the RCA for auditability.

## Checkpointing

After every successful transition:

1. Serialize `InvestigationState` to JSONB.
2. Insert `investigation_checkpoints` row.
3. Update `investigations.current_state`.

Resume loads latest checkpoint and continues from `current_step`.

## Approval Gate

`AWAITING_APPROVAL` is terminal for the autonomous path. Only an authenticated `engineer` or `admin` may:

- Approve → sandbox execution job enqueued
- Reject → record reason, mark investigation completed with rejection
- Cancel → abort without execution

Viewers cannot transition this state.
