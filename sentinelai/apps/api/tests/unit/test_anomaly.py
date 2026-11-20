from app.detection.anomaly import score_against_baseline


def test_insufficient_baseline_not_anomalous() -> None:
    score = score_against_baseline(
        metric_name="http_error_rate",
        service_name="api-gateway",
        current_value=0.5,
        baseline_values=[0.01, 0.02],
        min_samples=5,
    )
    assert not score.is_anomalous
    assert "Insufficient baseline" in score.explanation


def test_z_score_detects_spike() -> None:
    baseline = [0.01, 0.012, 0.009, 0.011, 0.01, 0.013, 0.008, 0.01]
    score = score_against_baseline(
        metric_name="http_error_rate",
        service_name="api-gateway",
        current_value=0.45,
        baseline_values=baseline,
    )
    assert score.is_anomalous
    assert score.z_score > 3
    assert score.severity_hint == "high"
    assert "z=" in score.explanation


def test_normal_value_not_anomalous() -> None:
    baseline = [0.01, 0.012, 0.009, 0.011, 0.01, 0.013, 0.008, 0.01]
    score = score_against_baseline(
        metric_name="http_error_rate",
        service_name="api-gateway",
        current_value=0.011,
        baseline_values=baseline,
    )
    assert not score.is_anomalous
    assert score.severity_hint == "none"
