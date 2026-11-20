# SENTINELAI Architecture Proposal

**Product:** Autonomous AI Operations and Incident Intelligence Platform  
**Status:** Milestone 1 — Approved for implementation  
**Version:** 0.1.0

## 1. Mission

SENTINELAI is an end-to-end AI-powered SRE platform that:

1. Ingests telemetry from simulated microservices (logs, metrics, traces, deployments).
2. Detects incidents via deterministic rules and explainable anomaly scoring.
3. Investigates root causes through a coordinated multi-agent state machine.
4. Evaluates its own findings against evidence.
5. Proposes sandboxed remediation requiring explicit human approval.

## 2. System Context

```
┌─────────────┐   OTLP/HTTP    ┌──────────────┐   REST/WS    ┌─────────────┐
│  Simulator  │───────────────▶│  API Backend │◀────────────▶│  Web (Next) │
│  4 services │                │  FastAPI     │              │             │
└──────┬──────┘                └──────┬───────┘              └─────────────┘
       │                              │
       │ scrape                       │ SQL / Redis / pgvector
       ▼                              ▼
┌─────────────┐                ┌──────────────┐
│ Prometheus  │                │ PostgreSQL   │
└──────┬──────┘                │ Redis        │
       │                       └──────────────┘
       ▼
┌─────────────┐   scheduled    ┌──────────────┐
│  Grafana    │◀───────────────│   Airflow    │
└─────────────┘   eval jobs    └──────────────┘
                                      │
                               ┌──────▼───────┐
                               │  MCP Server  │
                               │  (tools)     │
                               └──────────────┘
```

## 3. Architectural Principles

| Principle | Implementation |
|-----------|----------------|
| Real backend functionality | All dashboard data from DB/Prometheus; no hardcoded live metrics |
| Type-safe contracts | Pydantic v2 + OpenAPI + shared TypeScript types |
| Evidence-linked AI | Every hypothesis carries `evidence_refs[]` to telemetry IDs |
| Human approval gates | Remediation state machine: proposed → approved/rejected → executed |
| Provider-agnostic AI | `AIProvider` protocol; OpenAI, Anthropic, Local adapters |
| Measurable ops | Token/cost/latency counters; evaluation dataset versioning |
| Observable & auditable | OpenTelemetry + `audit_events` table for every privileged action |
| Honest claims | No fabricated benchmarks; evaluation scores computed from runs |

## 4. Component Breakdown

### 4.1 `apps/api` — Control Plane

- **Auth:** JWT (access + refresh), bcrypt passwords, RBAC (`admin`, `engineer`, `viewer`).
- **Telemetry ingestion:** OTLP-compatible JSON endpoints + batch writers.
- **Detection:** Rule engine + baseline anomaly scorer (z-score / EWMA; documented, evaluated).
- **Agents:** Explicit Python state machine (not LangChain).
- **MCP:** Read-only investigation tools vs permissioned remediation tools.
- **Remediation:** Plan generation + sandboxed executor (simulator only).
- **Evaluation:** Dataset runners, metrics persistence, CI regression gates.

### 4.2 `apps/simulator` — Telemetry Source

Four FastAPI services: Gateway, User, Order, Payment. Shared failure scenarios with `seed` + `duration_seconds`. Emit OTLP logs/metrics/traces to the API and Prometheus.

### 4.3 `apps/web` — Operations UI

Next.js App Router, dark-first SaaS UI, SSE for live incident/investigation updates. All pages bind to real APIs.

### 4.4 `packages/shared-contracts`

Canonical OpenAPI, JSON Schema, and generated/hand-maintained TypeScript + Python models for cross-app consistency.

### 4.5 Infrastructure

Docker Compose: postgres (pgvector), redis, prometheus, grafana, api, web, simulator services, airflow (optional profile), mcp.

## 5. Data Flow — Incident Lifecycle

```
Telemetry → Persist → Detect (rules/anomaly) → Alert grouping → Incident
    → Investigation SM → Agent tools (MCP/internal) → RCA + evidence
    → Remediation plan → Human approval → Sandbox execute → Audit
    → Recovery detection → Incident resolve → Evaluation sample
```

## 6. Agent Orchestration

See [AGENT_STATE_MACHINE.md](./AGENT_STATE_MACHINE.md).

Key guarantees:

- Typed `InvestigationState` with checkpointing in PostgreSQL.
- Bounded retries, timeouts, max tool calls, token budgets.
- Deterministic fallback when LLM unavailable.
- Never fabricate telemetry; tools return only DB/Prometheus data.

## 7. Security Model (Summary)

See [security/THREAT_MODEL.md](./security/THREAT_MODEL.md).

- Logs/external tool results treated as untrusted (prompt-injection resistant framing).
- Secret redaction before logging or LLM context.
- Remediation tools require `engineer`/`admin` + explicit approval record.
- Rate limiting, secure headers, CORS allowlist.

## 8. Technology Pinning (Initial)

| Layer | Choice | Notes |
|-------|--------|-------|
| Python | 3.12 | API + simulator |
| FastAPI | 0.115.x | Async ASGI |
| SQLAlchemy | 2.0.x | Async engine |
| Alembic | 1.14.x | Migrations |
| Pydantic | 2.x | Schemas |
| Next.js | 15.x | App Router |
| React | 19.x | UI |
| Tailwind | 3.4.x | Styling |
| PostgreSQL | 16 + pgvector | Primary store |
| Redis | 7.x | Cache/queue/pubsub |
| Prometheus | 2.x | Metrics |
| Grafana | 11.x | Dashboards |

Exact pins live in each app’s lock/requirements files.

## 9. Non-Goals (v0.1)

- Connecting remediation to real production clusters.
- Claiming ML anomaly detection beyond the implemented baseline scorer.
- Fabricated evaluation leaderboards.
- LangChain / LangGraph dependency.

## 10. Milestone Map

See [MILESTONES.md](./MILESTONES.md).
