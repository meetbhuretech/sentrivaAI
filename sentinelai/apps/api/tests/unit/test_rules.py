from sentinelai_contracts import Severity

from app.detection.rules import (
    DetectionThresholds,
    rule_error_rate,
    rule_latency_p95,
    rule_redis_connection_errors,
)


def test_error_rate_thresholds() -> None:
    t = DetectionThresholds(error_rate_high=0.05, error_rate_critical=0.25)
    assert rule_error_rate("api-gateway", 0.01, t) is None
    high = rule_error_rate("api-gateway", 0.10, t)
    assert high is not None
    assert high.severity == Severity.HIGH
    assert high.fingerprint == "error_rate_threshold:api-gateway"
    crit = rule_error_rate("api-gateway", 0.40, t)
    assert crit is not None
    assert crit.severity == Severity.CRITICAL


def test_latency_rule() -> None:
    t = DetectionThresholds(latency_p95_ms_high=500, latency_p95_ms_critical=2000)
    assert rule_latency_p95("order-service", 100, t) is None
    alert = rule_latency_p95("order-service", 800, t)
    assert alert is not None
    assert alert.rule_id == "latency_p95_threshold"


def test_redis_rule_requires_count() -> None:
    assert rule_redis_connection_errors("payment-service", 1) is None
    alert = rule_redis_connection_errors("payment-service", 3)
    assert alert is not None
    assert "Redis" in alert.title
