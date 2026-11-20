# Milestone Checklist

## Milestone 1 — Foundations ✅
- [x] Inspect repository (empty — greenfield)
- [x] Architecture proposal
- [x] Directory structure
- [x] Database schema document
- [x] API contract document
- [x] Agent state machine document
- [x] Shared contracts package (OpenAPI + Python/TS enums)
- [x] Initial README + `.env.example`
- [x] Docker Compose skeleton (postgres, redis, prometheus, grafana, api)
- [x] ADR-001 stack choices

## Milestone 2 — Backend Core ✅
- [x] FastAPI app bootstrap (settings, logging, CORS, security headers, rate limit)
- [x] SQLAlchemy models + Alembic initial migration
- [x] JWT auth + RBAC + password hashing
- [x] Core APIs (auth, overview, services, incidents, audit, health)
- [x] Audit event writer + secret redaction
- [x] Unit + integration + security tests for auth/RBAC
- [x] Lint green (`ruff`); **11 pytest tests passing**

## Milestone 3 — Simulator & Telemetry ✅
- [x] Four simulator services + shared library (gateway, user, order, payment)
- [x] Scenario runner (seed + duration) — 8 reproducible scenarios
- [x] Telemetry emission to API (logs/metrics/traces/deployments)
- [x] Ingestion endpoints + persistence + query APIs
- [x] Control-plane `/simulator/scenarios` proxy (engineer+)
- [x] Prometheus scrape config + `/metrics` on simulators
- [x] Integration tests for ingest/query (**13 API tests passing**)
- [x] Live verified: scenario raises real `http_error_rate` in overview

## Milestone 4 — Incident Detection ✅
- [x] Deterministic rule engine (error rate, latency, CPU/mem, health, Redis, timeouts, DB pool)
- [x] Explainable z-score anomaly scorer (documented; not claimed as ML)
- [x] Alert → incident grouping, dedup, severity, lifecycle, recovery
- [x] `POST /alerts/evaluate` + background scheduler
- [x] Detection tests — **22 pytest tests passing**

## Milestone 5 — AI Providers & Agents ✅
- [x] `AIProvider` protocol + OpenAI/Anthropic/Local/Deterministic adapters
- [x] Structured outputs (JSON) with anti-hallucination evidence filtering
- [x] Investigation state machine with DB checkpoints
- [x] Specialized agents (log/metrics/trace/deployment) + deterministic fallback
- [x] Documented confidence formula + RCA with evidence refs
- [x] Token/cost estimation hooks (pricing table documented)
- [x] Investigation API + tests — **25 pytest tests passing**

## Milestone 6 — Evidence, MCP, Approvals ✅
- [x] Evidence evaluator (ref existence check during investigation)
- [x] MCP HTTP tool server: read-only vs remediation scopes
- [x] Permission scopes + allowlist validation
- [x] Approval gate wiring

## Milestone 7 — Remediation Sandbox ✅
- [x] Allowlisted remediation actions only
- [x] Sandbox executor against simulator (no prod touch)
- [x] Approval/reject/cancel APIs
- [x] Audit trail + security tests — **27 pytest tests passing**

## Milestone 8 — Evaluation & MLOps ✅
- [x] Versioned incident evaluation dataset (`datasets/evaluation/v1`)
- [x] Evaluation runner + measured metrics (no fabricated scores)
- [x] Model comparison storage + API
- [x] Airflow DAG for scheduled eval
- [x] Tests — **28 pytest tests passing**

## Milestone 9 — Frontend ✅
- [x] Next.js app + design system (dark-first, IBM Plex, teal accent)
- [x] All 11 pages wired to real APIs
- [x] SSE live updates (`/overview/stream`, `/investigations/{id}/stream`)
- [x] Charts, timeline, evidence viewer, approval modal
- [x] Production build green; Compose `web` service enabled

## Milestone 10 — Hardening & Docs ✅
- [x] GitHub Actions CI (api lint/pytest, web build, Playwright e2e)
- [x] Playwright e2e core flows (login → overview, auth redirect)
- [x] Security tests expanded (SSE auth gate)
- [x] Demo walkthrough + screenshot placeholders; README updated
