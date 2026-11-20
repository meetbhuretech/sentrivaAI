# Incident Detection

## Deterministic rules

| Rule ID | Signal | Default thresholds |
|---------|--------|--------------------|
| `error_rate_threshold` | latest `http_error_rate` | high ≥ 0.05, critical ≥ 0.25 |
| `latency_p95_threshold` | latest `http_latency_p95_ms` | high ≥ 500, critical ≥ 2000 |
| `memory_pressure` | latest `memory_percent` | high ≥ 85, critical ≥ 95 |
| `cpu_saturation` | latest `cpu_percent` | medium ≥ 85 |
| `health_check_failed` | service status | unhealthy/unknown |
| `dependency_timeouts` | ERROR/WARN log patterns | ≥ 3 matches in lookback |
| `redis_connection_failure` | Redis error logs | ≥ 2 matches |
| `db_pool_saturation` | `db_pool_usage_ratio` | ≥ 0.9 |

## Anomaly scoring (not ML)

Method: **population z-score** against a baseline window (default 60 minutes, excluding current lookback).

```
z = (current - mean) / std
|z| >= 2 → anomalous (medium)
|z| >= 3 → strongly anomalous (high)
```

Every score includes `explanation`, `baseline_mean`, `baseline_std`, and `sample_count`.
Insufficient baseline (< 5 samples) → scoring skipped (not anomalous).

## Lifecycle

1. Rules + anomaly produce candidate alerts with fingerprints.
2. Dedup: firing alert with same fingerprint is updated, not duplicated.
3. Grouping: candidates merge into open incidents that share a service.
4. Recovery: fingerprints no longer firing → alert resolved; incidents with zero firing alerts → resolved + MTTR.

## API

- `POST /api/v1/alerts/evaluate` (engineer+) — one detection cycle
- `GET /api/v1/alerts` — list/filter alerts
- `GET /api/v1/incidents/{id}/timeline` — alert firing/resolved events

Background scheduler: `ENABLE_DETECTION_SCHEDULER=true`, `DETECTION_INTERVAL_SECONDS=30`.
