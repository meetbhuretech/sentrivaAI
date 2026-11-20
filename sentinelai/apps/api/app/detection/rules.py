"""Deterministic detection rules.

Each rule returns zero or more CandidateAlerts with fingerprints for deduplication.
Thresholds are configurable; defaults are documented and conservative for demos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sentinelai_contracts import Severity


@dataclass
class CandidateAlert:
    rule_id: str
    service_name: str
    severity: Severity
    title: str
    description: str
    fingerprint: str
    labels: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DetectionThresholds:
    error_rate_high: float = 0.05
    error_rate_critical: float = 0.25
    latency_p95_ms_high: float = 500.0
    latency_p95_ms_critical: float = 2000.0
    memory_percent_high: float = 85.0
    memory_percent_critical: float = 95.0
    cpu_percent_high: float = 85.0
    health_unhealthy: bool = True
    dependency_timeout_log_count: int = 3
    db_pool_saturation_ratio: float = 0.9


def rule_error_rate(
    service_name: str,
    error_rate: float,
    thresholds: DetectionThresholds,
) -> CandidateAlert | None:
    if error_rate >= thresholds.error_rate_critical:
        severity = Severity.CRITICAL
    elif error_rate >= thresholds.error_rate_high:
        severity = Severity.HIGH
    else:
        return None
    return CandidateAlert(
        rule_id="error_rate_threshold",
        service_name=service_name,
        severity=severity,
        title=f"High error rate on {service_name}",
        description=(
            f"Observed http_error_rate={error_rate:.4f} "
            f"(high>={thresholds.error_rate_high}, critical>={thresholds.error_rate_critical})"
        ),
        fingerprint=f"error_rate_threshold:{service_name}",
        labels={"metric": "http_error_rate", "value": error_rate},
        annotations={
            "threshold_high": thresholds.error_rate_high,
            "threshold_critical": thresholds.error_rate_critical,
        },
    )


def rule_latency_p95(
    service_name: str,
    p95_ms: float,
    thresholds: DetectionThresholds,
) -> CandidateAlert | None:
    if p95_ms >= thresholds.latency_p95_ms_critical:
        severity = Severity.CRITICAL
    elif p95_ms >= thresholds.latency_p95_ms_high:
        severity = Severity.HIGH
    else:
        return None
    return CandidateAlert(
        rule_id="latency_p95_threshold",
        service_name=service_name,
        severity=severity,
        title=f"Elevated p95 latency on {service_name}",
        description=(
            f"Observed http_latency_p95_ms={p95_ms:.1f} "
            f"(high>={thresholds.latency_p95_ms_high}, critical>={thresholds.latency_p95_ms_critical})"
        ),
        fingerprint=f"latency_p95_threshold:{service_name}",
        labels={"metric": "http_latency_p95_ms", "value": p95_ms},
    )


def rule_memory_pressure(
    service_name: str,
    memory_percent: float,
    thresholds: DetectionThresholds,
) -> CandidateAlert | None:
    if memory_percent >= thresholds.memory_percent_critical:
        severity = Severity.CRITICAL
    elif memory_percent >= thresholds.memory_percent_high:
        severity = Severity.HIGH
    else:
        return None
    return CandidateAlert(
        rule_id="memory_pressure",
        service_name=service_name,
        severity=severity,
        title=f"Memory pressure on {service_name}",
        description=f"Observed memory_percent={memory_percent:.1f}",
        fingerprint=f"memory_pressure:{service_name}",
        labels={"metric": "memory_percent", "value": memory_percent},
    )


def rule_cpu_saturation(
    service_name: str,
    cpu_percent: float,
    thresholds: DetectionThresholds,
) -> CandidateAlert | None:
    if cpu_percent < thresholds.cpu_percent_high:
        return None
    return CandidateAlert(
        rule_id="cpu_saturation",
        service_name=service_name,
        severity=Severity.MEDIUM,
        title=f"CPU saturation on {service_name}",
        description=f"Observed cpu_percent={cpu_percent:.1f} (>= {thresholds.cpu_percent_high})",
        fingerprint=f"cpu_saturation:{service_name}",
        labels={"metric": "cpu_percent", "value": cpu_percent},
    )


def rule_health_check_failed(
    service_name: str,
    status: str,
) -> CandidateAlert | None:
    if status not in {"unhealthy", "unknown"}:
        return None
    severity = Severity.CRITICAL if status == "unhealthy" else Severity.MEDIUM
    return CandidateAlert(
        rule_id="health_check_failed",
        service_name=service_name,
        severity=severity,
        title=f"Service health check {status}: {service_name}",
        description=f"Service status is '{status}'",
        fingerprint=f"health_check_failed:{service_name}",
        labels={"status": status},
    )


def rule_dependency_timeouts(
    service_name: str,
    timeout_log_count: int,
    thresholds: DetectionThresholds,
) -> CandidateAlert | None:
    if timeout_log_count < thresholds.dependency_timeout_log_count:
        return None
    return CandidateAlert(
        rule_id="dependency_timeouts",
        service_name=service_name,
        severity=Severity.HIGH,
        title=f"Repeated dependency timeouts on {service_name}",
        description=(
            f"Found {timeout_log_count} timeout-related ERROR logs "
            f"(threshold={thresholds.dependency_timeout_log_count})"
        ),
        fingerprint=f"dependency_timeouts:{service_name}",
        labels={"timeout_log_count": timeout_log_count},
    )


def rule_db_pool_saturation(
    service_name: str,
    pool_usage_ratio: float,
    thresholds: DetectionThresholds,
) -> CandidateAlert | None:
    if pool_usage_ratio < thresholds.db_pool_saturation_ratio:
        return None
    return CandidateAlert(
        rule_id="db_pool_saturation",
        service_name=service_name,
        severity=Severity.HIGH,
        title=f"Database connection pool saturation on {service_name}",
        description=(
            f"pool_usage_ratio={pool_usage_ratio:.2f} "
            f"(threshold={thresholds.db_pool_saturation_ratio})"
        ),
        fingerprint=f"db_pool_saturation:{service_name}",
        labels={"metric": "db_pool_usage_ratio", "value": pool_usage_ratio},
    )


def rule_redis_connection_errors(
    service_name: str,
    redis_error_count: int,
) -> CandidateAlert | None:
    if redis_error_count < 2:
        return None
    return CandidateAlert(
        rule_id="redis_connection_failure",
        service_name=service_name,
        severity=Severity.HIGH,
        title=f"Redis connection failures on {service_name}",
        description=f"Found {redis_error_count} Redis connection error logs",
        fingerprint=f"redis_connection_failure:{service_name}",
        labels={"redis_error_count": redis_error_count},
    )
