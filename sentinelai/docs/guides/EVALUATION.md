# Evaluation Methodology

## Dataset

Versioned under `datasets/evaluation/<version>/manifest.json`.

Each case includes:
- seed telemetry (metrics/logs/optional deployment)
- expected root-cause keywords (deterministic check)
- expected tool names (selection accuracy)

## Computed metrics (never fabricated)

| Metric | Computation |
|--------|-------------|
| root_cause_accuracy | Fraction of expected keywords found in RCA text |
| evidence_grounding | Fraction of RCA evidence refs with kind+id |
| tool_selection_accuracy | Intersection of used vs expected tools |
| investigation_completion | 1 if status=`awaiting_approval` and RCA present |
| avg_investigation_latency_seconds | Wall time per case |
| avg_estimated_cost_usd | From investigation cost accounting |
| pass_rate | Cases meeting deterministic pass thresholds |
| remediation_quality | **Always null** until human review labels exist |

## Human review

Subjective scores require dual-engineer review before writing labels into the dataset.
CI asserts only deterministic fields.

## API

- `POST /api/v1/evaluation/runs`
- `GET /api/v1/evaluation/runs/{id}/results`
- `GET /api/v1/evaluation/comparisons`
