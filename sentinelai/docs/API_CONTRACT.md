# API Contract (v0.1)

Base URL: `http://localhost:8000/api/v1`  
Auth: `Authorization: Bearer <access_token>`  
Content-Type: `application/json`

Canonical OpenAPI will live at `packages/shared-contracts/openapi/openapi.yaml` and be served at `/openapi.json`.

## Auth

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/auth/register` | admin (bootstrap: first user open) | Create user |
| POST | `/auth/login` | public | Returns access + refresh JWT |
| POST | `/auth/refresh` | public | Refresh access token |
| GET | `/auth/me` | any authenticated | Current user |

## Overview / Dashboard

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/overview` | viewer+ | Aggregated ops stats |
| GET | `/overview/stream` | viewer+ | SSE live updates |

Query: `from`, `to`, `service` (optional filters).

Response includes: service counts, incident counts by severity, request/error rates, latency percentiles, CPU/memory averages, MTTR, recent deployments, AI investigation status — all computed from persisted/telemetry data.

## Services

| Method | Path | Roles |
|--------|------|-------|
| GET | `/services` | viewer+ |
| GET | `/services/{id}` | viewer+ |
| GET | `/services/{id}/health` | viewer+ |
| GET | `/services/dependencies` | viewer+ |

## Incidents

| Method | Path | Roles |
|--------|------|-------|
| GET | `/incidents` | viewer+ |
| GET | `/incidents/{id}` | viewer+ |
| POST | `/incidents/{id}/investigate` | engineer+ |
| PATCH | `/incidents/{id}` | engineer+ | status transitions |
| GET | `/incidents/{id}/timeline` | viewer+ |

## Alerts

| Method | Path | Roles |
|--------|------|-------|
| GET | `/alerts` | viewer+ |
| POST | `/alerts/evaluate` | engineer+ | force detection cycle |

## Telemetry

| Method | Path | Roles |
|--------|------|-------|
| POST | `/telemetry/logs` | internal/service | ingest |
| POST | `/telemetry/metrics` | internal/service | ingest |
| POST | `/telemetry/traces` | internal/service | ingest |
| POST | `/telemetry/deployments` | internal/service | ingest |
| GET | `/telemetry/logs` | viewer+ | search + pagination |
| GET | `/telemetry/metrics` | viewer+ | query samples |
| GET | `/telemetry/traces` | viewer+ | list/filter |
| GET | `/telemetry/traces/{trace_id}` | viewer+ | detail + spans |

Filters: `service`, `from`, `to`, `level`, `trace_id`, `correlation_id`, `q`, `page`, `page_size`.

## Investigations

| Method | Path | Roles |
|--------|------|-------|
| GET | `/investigations` | viewer+ |
| GET | `/investigations/{id}` | viewer+ |
| GET | `/investigations/{id}/timeline` | viewer+ |
| GET | `/investigations/{id}/evidence` | viewer+ |
| POST | `/investigations/{id}/cancel` | engineer+ |
| GET | `/investigations/{id}/stream` | viewer+ | SSE step updates |

## Remediation

| Method | Path | Roles |
|--------|------|-------|
| GET | `/remediations` | viewer+ |
| GET | `/remediations/{id}` | viewer+ |
| POST | `/remediations/{id}/approve` | engineer+ |
| POST | `/remediations/{id}/reject` | engineer+ |
| POST | `/remediations/{id}/cancel` | engineer+ |
| GET | `/remediations/{id}/execution` | viewer+ |

## Simulator Control

| Method | Path | Roles |
|--------|------|-------|
| GET | `/simulator/scenarios` | viewer+ |
| POST | `/simulator/scenarios/{name}/run` | engineer+ | body: `{seed, duration_seconds, services?}` |
| POST | `/simulator/scenarios/stop` | engineer+ |

## Evaluation / MLOps

| Method | Path | Roles |
|--------|------|-------|
| GET | `/evaluation/datasets` | viewer+ |
| GET | `/evaluation/runs` | viewer+ |
| POST | `/evaluation/runs` | engineer+ | compare models |
| GET | `/evaluation/runs/{id}` | viewer+ |
| GET | `/evaluation/comparisons` | viewer+ |

## Audit

| Method | Path | Roles |
|--------|------|-------|
| GET | `/audit` | admin | pagination + filters |

## Settings

| Method | Path | Roles |
|--------|------|-------|
| GET | `/settings` | engineer+ |
| PATCH | `/settings` | admin | detection thresholds, budgets |

## Error Envelope

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient role",
    "details": {}
  }
}
```

## Pagination

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 0
}
```
