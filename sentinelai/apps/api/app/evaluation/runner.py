"""Evaluation runner over versioned incident cases.

All metrics are computed from actual investigation outputs.
Subjective remediation quality is left null unless a human-reviewed label exists.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import InvestigationOrchestrator
from app.detection.engine import DetectionEngine
from app.detection.rules import DetectionThresholds
from app.models.evaluation import EvaluationRun, EvaluationRunResult
from app.models.service import Deployment, Service
from app.models.telemetry import MetricSample, TelemetryLog

logger = logging.getLogger(__name__)

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[4] / "datasets" / "evaluation" / "v1" / "manifest.json"
)


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_DATASET
    with manifest_path.open() as f:
        return json.load(f)


def _keyword_hit(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    lower = text.lower()
    hits = sum(1 for k in keywords if k.lower() in lower)
    return hits / len(keywords)


async def run_evaluation(
    db: AsyncSession,
    *,
    dataset_version: str = "v1",
    provider: str = "deterministic",
    model: str = "rules-v1",
    prompt_version: str = "v1",
    manifest_path: Path | None = None,
) -> EvaluationRun:
    manifest = load_manifest(manifest_path)
    if manifest.get("dataset_version") != dataset_version and dataset_version != "v1":
        # Allow explicit path override; otherwise require match
        pass

    run = EvaluationRun(
        id=uuid4(),
        dataset_version=dataset_version,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        status="running",
        config={"manifest": str(manifest_path or DEFAULT_DATASET)},
    )
    db.add(run)
    await db.flush()

    case_results: list[EvaluationRunResult] = []
    started = time.perf_counter()
    try:
        for case in manifest["cases"]:
            result = await _run_case(db, case, provider=provider, model=model)
            row = EvaluationRunResult(
                run_id=run.id,
                case_id=case["case_id"],
                passed=result["passed"],
                scores=result["scores"],
                details=result["details"],
            )
            db.add(row)
            case_results.append(row)
        await db.flush()

        metrics = _aggregate([r.scores for r in case_results], case_results, started)
        run.metrics = metrics
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
    except Exception as exc:  # noqa: BLE001
        logger.exception("evaluation run failed")
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(UTC)
    await db.flush()
    return run


async def _run_case(
    db: AsyncSession,
    case: dict[str, Any],
    *,
    provider: str,
    model: str,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    for m in case.get("seed_metrics", []):
        db.add(
            MetricSample(
                timestamp=now,
                service_name=m["service_name"],
                metric_name=m["metric_name"],
                value=float(m["value"]),
                labels={"eval_case": case["case_id"]},
            )
        )
    for log in case.get("seed_logs", []):
        db.add(
            TelemetryLog(
                timestamp=now,
                service_name=log["service_name"],
                environment="local",
                level=log.get("level", "ERROR"),
                message=log["message"],
                attributes={"eval_case": case["case_id"]},
                raw={},
            )
        )
    if case.get("seed_deployment"):
        dep = case["seed_deployment"]
        svc = (
            await db.execute(select(Service).where(Service.name == dep["service_name"]))
        ).scalar_one_or_none()
        if svc:
            db.add(
                Deployment(
                    service_id=svc.id,
                    version=dep["version"],
                    status="success",
                    started_at=now,
                    completed_at=now,
                    notes=dep.get("notes"),
                    metadata_json={"eval_case": case["case_id"]},
                )
            )
    await db.flush()

    t0 = time.perf_counter()
    detection = await DetectionEngine(DetectionThresholds()).run(db)
    if not detection.incident_ids:
        return {
            "passed": False,
            "scores": {
                "root_cause_accuracy": 0.0,
                "evidence_grounding": 0.0,
                "tool_selection_accuracy": 0.0,
                "investigation_completion": 0.0,
                "latency_seconds": time.perf_counter() - t0,
            },
            "details": {"error": "detection produced no incident"},
        }

    incident_id = __import__("uuid").UUID(detection.incident_ids[0])
    orch = InvestigationOrchestrator(db)
    inv = await orch.start(incident_id, provider_name=provider, model=model)
    latency = time.perf_counter() - t0

    rca = inv.rca or {}
    cause_text = f"{rca.get('probable_root_cause', '')} {rca.get('summary', '')}"
    root_cause_accuracy = _keyword_hit(cause_text, case.get("expected_root_cause_keywords", []))

    evidence = rca.get("supporting_evidence") or []
    # Grounding: fraction of evidence refs that have kind+id
    if not evidence:
        evidence_grounding = 0.0
    else:
        evidence_grounding = sum(
            1 for e in evidence if isinstance(e, dict) and e.get("kind") and e.get("id")
        ) / len(evidence)

    tool_calls = (inv.state or {}).get("tool_calls") or []
    used_tools = {c.get("tool") for c in tool_calls}
    expected_tools = set(case.get("expected_tools") or [])
    if expected_tools:
        tool_selection_accuracy = len(used_tools & expected_tools) / len(expected_tools)
    else:
        tool_selection_accuracy = 1.0 if used_tools else 0.0

    completion = 1.0 if inv.status.value == "awaiting_approval" and rca else 0.0
    passed = (
        root_cause_accuracy >= 0.34
        and evidence_grounding >= 0.5
        and completion == 1.0
    )

    return {
        "passed": passed,
        "scores": {
            "root_cause_accuracy": round(root_cause_accuracy, 4),
            "evidence_grounding": round(evidence_grounding, 4),
            "tool_selection_accuracy": round(tool_selection_accuracy, 4),
            "investigation_completion": completion,
            "remediation_quality": None,  # requires human review — not fabricated
            "latency_seconds": round(latency, 4),
            "estimated_cost_usd": float(inv.estimated_cost_usd or 0),
        },
        "details": {
            "investigation_id": str(inv.id),
            "incident_id": str(incident_id),
            "provider": inv.provider,
            "model": inv.model,
            "tools_used": sorted(used_tools),
            "probable_root_cause": rca.get("probable_root_cause"),
            "confidence": rca.get("confidence"),
        },
    }


def _aggregate(
    score_dicts: list[dict[str, Any]],
    results: list[EvaluationRunResult],
    started: float,
) -> dict[str, Any]:
    n = len(results) or 1
    keys = [
        "root_cause_accuracy",
        "evidence_grounding",
        "tool_selection_accuracy",
        "investigation_completion",
    ]
    averages = {}
    for k in keys:
        values = [float(s.get(k) or 0) for s in score_dicts]
        averages[k] = round(sum(values) / n, 4)
    passed = sum(1 for r in results if r.passed)
    return {
        **averages,
        "false_positive_rate": None,  # not computed in v1 deterministic suite
        "investigation_completion_rate": averages["investigation_completion"],
        "human_intervention_rate": None,  # requires production telemetry
        "avg_investigation_latency_seconds": round(
            sum(float(s.get("latency_seconds") or 0) for s in score_dicts) / n, 4
        ),
        "avg_estimated_cost_usd": round(
            sum(float(s.get("estimated_cost_usd") or 0) for s in score_dicts) / n, 6
        ),
        "cases_total": len(results),
        "cases_passed": passed,
        "pass_rate": round(passed / n, 4),
        "wall_clock_seconds": round(time.perf_counter() - started, 4),
        "remediation_quality": None,
        "note": "Scores computed from this run only; remediation_quality requires human review.",
    }
