from app.agents.confidence import compute_confidence
from app.agents.state import AgentFindingModel, EvidenceRef, HypothesisModel


def test_confidence_formula_with_full_evidence() -> None:
    refs = [
        EvidenceRef(kind="log", id="1"),
        EvidenceRef(kind="metric", id="2"),
    ]
    hyp = HypothesisModel(
        statement="error_rate_threshold: High error rate on api-gateway",
        confidence=0.5,
        evidence_refs=refs,
    )
    findings = [
        AgentFindingModel(
            agent_name="log_investigation",
            summary="High error rate on api-gateway with redis failures",
            evidence_refs=refs,
        ),
        AgentFindingModel(
            agent_name="metrics_investigation",
            summary="error_rate elevated on api-gateway",
            evidence_refs=refs[:1],
        ),
    ]
    conf, comps = compute_confidence(
        top_hypothesis=hyp,
        findings=findings,
        grounded_refs=refs,
        signal_strength=1.0,
        temporal_alignment=0.7,
    )
    assert comps.evidence_coverage == 1.0
    assert 0.5 <= conf <= 1.0


def test_confidence_zero_without_evidence() -> None:
    hyp = HypothesisModel(statement="unknown", confidence=0.2, evidence_refs=[])
    conf, comps = compute_confidence(
        top_hypothesis=hyp,
        findings=[],
        grounded_refs=[],
        signal_strength=0.0,
        temporal_alignment=0.0,
    )
    assert comps.evidence_coverage == 0.0
    assert conf == 0.0
