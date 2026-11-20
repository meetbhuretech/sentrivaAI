# Demo walkthrough

End-to-end path using **real** telemetry, detection, investigation, approval, and evaluation. No fabricated dashboard numbers.

## Prerequisites

- PostgreSQL + Redis reachable (Compose or local)
- API on `:8000`, web on `:3000`, gateway simulator on `:8100` (optional for live traffic)
- Bootstrap admin from `.env.example`: `admin@example.com` / `ChangeMeAdmin123!`

## Local (dev)

```bash
# API
cd apps/api && source .venv/bin/activate
export DATABASE_URL='postgresql+asyncpg://sentinelai:sentinelai@localhost:5432/sentinelai'
export DATABASE_URL_SYNC='postgresql://sentinelai:sentinelai@localhost:5432/sentinelai'
export SECRET_KEY='dev-secret'
export SIMULATOR_INTERNAL_TOKEN='change-me-simulator-token'
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Web (Node 20+)
cd apps/web && cp .env.example .env.local
npm ci && npm run dev

# Optional gateway simulator
cd apps/simulator && source .venv/bin/activate
export SENTINELAI_API_URL=http://127.0.0.1:8000/api/v1
export SIMULATOR_INTERNAL_TOKEN=change-me-simulator-token
uvicorn gateway.main:app --host 127.0.0.1 --port 8100
```

## Demo path

1. **Login** at http://localhost:3000/login — opens Operations Overview.
2. Overview metrics come from SSE (`/overview/stream`) over persisted aggregates (zeros are honest when quiet).
3. **Trigger a scenario** (engineer+): `POST /api/v1/simulator/scenarios/{name}/run` with a seed, or let the gateway emit traffic until detection opens incidents.
4. **Incidents** → open one → **Investigate** (deterministic provider works without API keys).
5. **Investigations** → watch checkpoints via SSE; every finding/hypothesis carries evidence refs.
6. **Remediation** → approve or reject; execution hits the **sandbox allowlist** only.
7. **Evaluation** → run dataset `v1`; scores shown are measured from that run (never invented).
8. **Audit** → confirm start/approve/reject events with redacted secrets.

## Screenshots

Place PNG captures under `docs/screenshots/` when recording a portfolio walkthrough:

- `01-login.png`
- `02-overview.png`
- `03-incident-detail.png`
- `04-investigation.png`
- `05-remediation-approval.png`
- `06-evaluation.png`

## Compose

```bash
cp .env.example .env
docker compose up --build
```

Web: http://localhost:3000 · API docs: http://localhost:8000/docs · Grafana: http://localhost:3001
