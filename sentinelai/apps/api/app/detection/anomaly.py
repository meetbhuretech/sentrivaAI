"""Explainable baseline anomaly scoring.

Method: rolling mean + population standard deviation (z-score).
This is a classical statistical detector — not claimed as ML.

Score interpretation (documented):
  |z| < 2  → normal
  |z| >= 2 → anomalous (medium)
  |z| >= 3 → strongly anomalous (high)

Returns structured explanation for every score.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyScore:
    metric_name: str
    service_name: str
    value: float
    baseline_mean: float
    baseline_std: float
    sample_count: int
    z_score: float
    is_anomalous: bool
    severity_hint: str  # none | medium | high
    explanation: str


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _population_std(values: Sequence[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def score_against_baseline(
    *,
    metric_name: str,
    service_name: str,
    current_value: float,
    baseline_values: Sequence[float],
    z_medium: float = 2.0,
    z_high: float = 3.0,
    min_samples: int = 5,
) -> AnomalyScore:
    """Compute z-score of current_value vs baseline window.

    Requires min_samples baseline points; otherwise returns non-anomalous
    with explanation that baseline is insufficient.
    """
    n = len(baseline_values)
    if n < min_samples:
        return AnomalyScore(
            metric_name=metric_name,
            service_name=service_name,
            value=current_value,
            baseline_mean=0.0,
            baseline_std=0.0,
            sample_count=n,
            z_score=0.0,
            is_anomalous=False,
            severity_hint="none",
            explanation=(
                f"Insufficient baseline samples ({n}<{min_samples}); "
                "anomaly scoring skipped."
            ),
        )

    mean = _mean(baseline_values)
    std = _population_std(baseline_values, mean)
    if std < 1e-9:
        # Flat baseline — treat large absolute deviation as anomalous if present
        delta = abs(current_value - mean)
        if delta < 1e-9:
            return AnomalyScore(
                metric_name=metric_name,
                service_name=service_name,
                value=current_value,
                baseline_mean=mean,
                baseline_std=std,
                sample_count=n,
                z_score=0.0,
                is_anomalous=False,
                severity_hint="none",
                explanation="Baseline has zero variance; current equals mean.",
            )
        # Use relative deviation as a pseudo z for flat series
        z = delta / max(abs(mean), 1e-3)
        anomalous = z >= z_medium
        hint = "high" if z >= z_high else ("medium" if anomalous else "none")
        return AnomalyScore(
            metric_name=metric_name,
            service_name=service_name,
            value=current_value,
            baseline_mean=mean,
            baseline_std=std,
            sample_count=n,
            z_score=z,
            is_anomalous=anomalous,
            severity_hint=hint,
            explanation=(
                f"Flat baseline (std≈0). Relative deviation={z:.2f} "
                f"(medium>={z_medium}, high>={z_high})."
            ),
        )

    z = (current_value - mean) / std
    abs_z = abs(z)
    anomalous = abs_z >= z_medium
    if abs_z >= z_high:
        hint = "high"
    elif abs_z >= z_medium:
        hint = "medium"
    else:
        hint = "none"

    return AnomalyScore(
        metric_name=metric_name,
        service_name=service_name,
        value=current_value,
        baseline_mean=mean,
        baseline_std=std,
        sample_count=n,
        z_score=z,
        is_anomalous=anomalous,
        severity_hint=hint,
        explanation=(
            f"z=({current_value:.4f}-{mean:.4f})/{std:.4f}={z:.2f}; "
            f"|z|>={z_medium} → anomalous, |z|>={z_high} → high. "
            f"Baseline n={n}."
        ),
    )
