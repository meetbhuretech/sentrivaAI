# Database Schema

**Engine:** PostgreSQL 16 with `pgvector`  
**ORM:** SQLAlchemy 2.0 (async)  
**Migrations:** Alembic

## ER Overview

```
users ─┬─ audit_events
       ├─ remediation_approvals
       └─ evaluation_runs

services ─┬─ deployments
          ├─ service_dependencies
          └─ health_checks

incidents ─┬─ alerts
           ├─ investigations ─┬─ investigation_checkpoints
           │                  ├─ agent_findings
           │                  └─ hypotheses
           └─ remediation_plans ─ remediation_executions

telemetry_logs
telemetry_metrics (rollup samples; Prometheus is source of truth for scrape)
telemetry_traces ─ telemetry_spans
deployment_events

evaluation_datasets ─ evaluation_cases ─ evaluation_run_results
model_configs
prompt_versions
```

## Tables

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | CITEXT UNIQUE | |
| password_hash | TEXT | bcrypt |
| full_name | TEXT | |
| role | ENUM(admin,engineer,viewer) | |
| is_active | BOOLEAN | default true |
| created_at / updated_at | TIMESTAMPTZ | |

### `services`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | TEXT UNIQUE | e.g. `api-gateway` |
| display_name | TEXT | |
| environment | TEXT | `local` / `demo` |
| base_url | TEXT | simulator URL |
| status | ENUM(healthy,degraded,unhealthy,unknown) | |
| metadata | JSONB | |
| created_at / updated_at | TIMESTAMPTZ | |

### `service_dependencies`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| source_service_id | UUID FK | |
| target_service_id | UUID FK | |
| dependency_type | TEXT | http/db/redis/queue |
| UNIQUE(source, target, type) | | |

### `deployments`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| service_id | UUID FK | |
| version | TEXT | |
| commit_sha | TEXT | |
| status | ENUM(pending,success,failed,rolled_back) | |
| started_at / completed_at | TIMESTAMPTZ | |
| metadata | JSONB | config diffs, etc. |

### `telemetry_logs`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| timestamp | TIMESTAMPTZ | indexed |
| service_name | TEXT | indexed |
| environment | TEXT | |
| level | TEXT | DEBUG/INFO/WARN/ERROR |
| message | TEXT | |
| trace_id | TEXT | indexed |
| span_id | TEXT | |
| correlation_id | TEXT | indexed |
| attributes | JSONB | |
| raw | JSONB | |

Indexes: `(timestamp DESC)`, `(service_name, timestamp DESC)`, GIN on `attributes`.

### `telemetry_traces` / `telemetry_spans`
Trace header + child spans with duration_ms, status, parent_span_id, attributes.

### `metric_samples`
Periodic samples persisted for investigation queries (Prometheus remains scrape store):

| Column | Type |
|--------|------|
| id | UUID PK |
| timestamp | TIMESTAMPTZ |
| service_name | TEXT |
| metric_name | TEXT |
| value | DOUBLE PRECISION |
| labels | JSONB |

### `alerts`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| rule_id | TEXT | |
| service_name | TEXT | |
| severity | ENUM(critical,high,medium,low,info) | |
| title | TEXT | |
| description | TEXT | |
| status | ENUM(firing,resolved) | |
| fingerprint | TEXT | dedup key |
| started_at / resolved_at | TIMESTAMPTZ | |
| labels / annotations | JSONB | |
| incident_id | UUID FK NULL | |

### `incidents`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| title | TEXT | |
| status | ENUM(open,investigating,mitigating,resolved,closed) | |
| severity | ENUM(...) | |
| service_names | TEXT[] | |
| started_at / detected_at / resolved_at | TIMESTAMPTZ | |
| mttr_seconds | INT NULL | computed on resolve |
| summary | TEXT | |
| metadata | JSONB | |

### `investigations`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| incident_id | UUID FK | |
| status | ENUM (mirrors SM) | |
| current_step | TEXT | |
| provider / model / prompt_version | TEXT | |
| state | JSONB | full checkpoint blob |
| rca | JSONB | final RCA |
| token_usage | JSONB | |
| estimated_cost_usd | NUMERIC(10,6) | |
| started_at / completed_at / deadline_at | TIMESTAMPTZ | |
| error_message | TEXT NULL | |

### `investigation_checkpoints`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| investigation_id | UUID FK | |
| step | TEXT | |
| state | JSONB | |
| created_at | TIMESTAMPTZ | |

### `agent_findings`
Structured per-agent outputs with `evidence_refs UUID[]` / string refs to telemetry.

### `hypotheses`
Ranked hypotheses with confidence components and evidence refs.

### `remediation_plans`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| investigation_id | UUID FK | |
| incident_id | UUID FK | |
| status | ENUM(proposed,approved,rejected,cancelled,executing,succeeded,failed,rolled_back) | |
| problem_summary | TEXT | |
| rationale | TEXT | |
| actions | JSONB | exact sandbox actions (allowlisted) |
| risks | TEXT | |
| rollback_steps | JSONB | |
| expected_impact | TEXT | marked estimate |
| created_at | TIMESTAMPTZ | |

### `remediation_approvals`
Approver user_id, decision, reason, timestamp.

### `remediation_executions`
Sandbox run results, stdout/stderr (redacted), rollback status.

### `audit_events`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| actor_user_id | UUID NULL | |
| action | TEXT | |
| resource_type / resource_id | TEXT | |
| ip / user_agent | TEXT | |
| details | JSONB | redacted |
| created_at | TIMESTAMPTZ | |

### `evaluation_datasets` / `evaluation_cases` / `evaluation_runs` / `evaluation_run_results`
Versioned datasets; runs store provider/model/prompt/dataset versions and measured scores only.

### `model_configs` / `prompt_versions`
Registry for comparison UI.

## Vectors (optional enrichment)

`evidence_embeddings` (id, source_type, source_id, embedding vector(1536), metadata) for similarity search over findings. Not required for core RCA path in v0.1.

## Retention

Configurable; default demo retention 7 days for high-volume telemetry tables.
