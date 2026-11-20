# SENTINELAI

**Autonomous AI Operations and Incident Intelligence Platform**

Production-oriented portfolio application that ingests telemetry from simulated microservices, detects incidents, investigates root causes through coordinated AI agents, evaluates evidence, and proposes sandboxed remediation requiring human approval.

> This is a demo platform. Remediation never targets real production infrastructure by default. Evaluation scores are only those computed from actual runs — none are fabricated.

## Architecture (short)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full proposal.

- **Web:** Next.js App Router + TypeScript + Tailwind + shadcn/ui + Recharts  
- **API:** FastAPI + SQLAlchemy + Alembic + JWT/RBAC  
- **Simulator:** API Gateway, User, Order, Payment services with seeded failure scenarios  
- **Agents:** Explicit Python state machine (not LangChain) with checkpoints, budgets, deterministic fallback  
- **Data:** PostgreSQL (pgvector) + Redis + Prometheus + Grafana  
- **Interop:** MCP server for investigation/remediation tools  

## Milestone status

| Milestone | Status |
|-----------|--------|
| 1 Foundations (architecture, contracts, schema) | Done |
| 2 Backend, auth, migrations, API tests | Done (11 tests passing) |
| 3 Simulator + telemetry | Done (live ingest verified) |
| 4 Incident detection | Done |
| 5 AI providers + multi-agent investigation | Done |
| 6 Evidence, MCP, approvals | Done |
| 7 Remediation sandbox | Done |
| 8 Model evaluation / MLOps | Done |
| 9 Frontend integration | Done (SSE + real APIs) |
| 10 CI/CD, security/e2e, docs | Done |

Details: [docs/MILESTONES.md](docs/MILESTONES.md)

## Quick start (Docker Compose)

```bash
cd sentinelai
cp .env.example .env
# Optionally set OPENAI_API_KEY / ANTHROPIC_API_KEY for LLM mode
docker compose up --build
```

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

Default bootstrap admin (from `.env.example`): `admin@example.com` / `ChangeMeAdmin123!` — change immediately after first login.

### Local web (without Compose web service)

```bash
cd apps/web && cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
# Node 20+
npm ci && npm run dev
```

Full demo path: [docs/guides/DEMO_WALKTHROUGH.md](docs/guides/DEMO_WALKTHROUGH.md)

### Tests

```bash
# API — 31 pytest (ruff + pytest in CI)
cd apps/api && pytest -q

# Web e2e (API + web must be running)
cd apps/web && npm run test:e2e
```

## Documentation

| Doc | Path |
|-----|------|
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Directory structure | [docs/DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md) |
| Database schema | [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) |
| API contract | [docs/API_CONTRACT.md](docs/API_CONTRACT.md) |
| Agent state machine | [docs/AGENT_STATE_MACHINE.md](docs/AGENT_STATE_MACHINE.md) |
| Demo walkthrough | [docs/guides/DEMO_WALKTHROUGH.md](docs/guides/DEMO_WALKTHROUGH.md) |
| Milestones | [docs/MILESTONES.md](docs/MILESTONES.md) |
| ADR-001 | [docs/adr/001-stack-and-orchestration.md](docs/adr/001-stack-and-orchestration.md) |

## Design principles

1. Real backend functionality — no fake live dashboard data.  
2. Every AI conclusion links to evidence references.  
3. Dangerous operations require explicit human approval.  
4. Model-independent AI provider architecture.  
5. Cost, latency, reliability, and evaluation are measurable.  
6. Never claim benchmarks that have not been measured.

## License

Portfolio / demonstration use. Add a production license before any commercial deployment.
