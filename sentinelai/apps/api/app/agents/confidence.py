"""Documented confidence score calculation for RCA."""

from __future__ import annotations

from app.agents.state import (
    AgentFindingModel,
    ConfidenceComponents,
    EvidenceRef,
    HypothesisModel,
)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def compute_confidence(
    *,
    top_hypothesis: HypothesisModel,
    findings: list[AgentFindingModel],
    grounded_refs: list[EvidenceRef],
    signal_strength: float,
    temporal_alignment: float,
) -> tuple[float, ConfidenceComponents]:
    """
    confidence = clamp(
      0.35 * evidence_coverage
    + 0.25 * cross_agent_agreement
    + 0.20 * signal_strength
    + 0.20 * temporal_alignment
    , 0, 1)
    """
    claimed = top_hypothesis.evidence_refs
    if not claimed:
        evidence_coverage = 0.0
    else:
        grounded_ids = {(r.kind, r.id) for r in grounded_refs}
        hits = sum(1 for r in claimed if (r.kind, r.id) in grounded_ids)
        evidence_coverage = hits / len(claimed)

    if not findings:
        cross_agent_agreement = 0.0
    else:
        agreeing = 0
        for f in findings:
            text = (f.summary + " " + str(f.details)).lower()
            keywords = [w for w in top_hypothesis.statement.lower().split() if len(w) > 4]
            if keywords and sum(1 for k in keywords if k in text) >= max(1, len(keywords) // 3):
                agreeing += 1
        cross_agent_agreement = agreeing / len(findings)

    components = ConfidenceComponents(
        evidence_coverage=clamp(evidence_coverage),
        cross_agent_agreement=clamp(cross_agent_agreement),
        signal_strength=clamp(signal_strength),
        temporal_alignment=clamp(temporal_alignment),
    )
    confidence = clamp(
        0.35 * components.evidence_coverage
        + 0.25 * components.cross_agent_agreement
        + 0.20 * components.signal_strength
        + 0.20 * components.temporal_alignment
    )
    return confidence, components
