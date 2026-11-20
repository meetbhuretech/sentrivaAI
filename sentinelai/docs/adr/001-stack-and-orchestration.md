# ADR-001: Stack Choices and Agent Orchestration

## Status

Accepted

## Context

SENTINELAI must demonstrate production-oriented SRE + AI ops engineering: type-safe APIs, measurable AI, human approval gates, and observability — without becoming a LangChain demo or a fake dashboard.

## Decision

1. **Backend:** FastAPI + SQLAlchemy 2 async + Alembic + Pydantic v2 on Python 3.12.
2. **Frontend:** Next.js App Router + TypeScript + Tailwind + shadcn/ui + Recharts.
3. **Data:** PostgreSQL 16 with pgvector; Redis for cache/pubsub/queue coordination.
4. **Telemetry:** OpenTelemetry instrumentation; Prometheus + Grafana for metrics visualization; structured events also persisted in PostgreSQL for investigation queries.
5. **Agent orchestration:** Explicit Python finite-state machine with typed state, DB checkpointing, budgets, and deterministic fallback. **Do not depend on LangChain/LangGraph.**
6. **AI providers:** Protocol-based adapters (OpenAI, Anthropic, optional local) with structured outputs.
7. **Tool interoperability:** MCP server exposing read-only investigation tools separately from permissioned remediation tools.
8. **Remediation:** Allowlisted sandbox actions against the simulator only; never arbitrary shell from LLM output.
9. **Compose-first local demo:** Docker Compose brings up the full stack for reproducible demos.

## Consequences

- More code ownership of the agent loop (retries, checkpoints, budgets) vs. framework magic.
- Clearer auditability and evidence linking.
- Requires disciplined contract sharing between Python and TypeScript.
- Local LLM adapter may be limited; production demos can use cloud providers via env keys without hardcoding secrets.
