"""KMA Council - Council Orchestration, pipeline del 1 (KMA-005).

Deterministisk 11-stegspipeline (Notion sida 04, arkitektur 7).
Se pipeline2 for run_pipeline.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from kma.evidence import Evidence, EvidenceEngine, EvidenceStatus

from . import routing as _routing
from .contracts import load_contract
from .errors import IntakeError, PipelineError
from .models import (
    AgentContribution,
    AuditTrail,
    Conflict,
    CouncilDecision,
    DecisionStatus,
    Question,
)

__all__ = [
    "PIPELINE_STEPS",
    "CRITICAL_INTAKE_FIELDS",
    "check_intake",
    "PipelineResult",
]

PIPELINE_STEPS = (
    "intake",
    "classification",
    "missing_information_gate",
    "expert_routing",
    "parallel_analysis",
    "research_source_verification",
    "conflict_detection",
    "red_team_review",
    "chair_synthesis",
    "evidence_validation",
    "final_output",
)

CRITICAL_INTAKE_FIELDS = ("text",)

_EVIDENCE_TO_DECISION: dict[EvidenceStatus, DecisionStatus] = {
    EvidenceStatus.VERIFIED: DecisionStatus.VERIFIED,
    EvidenceStatus.PARTIALLY_VERIFIED: DecisionStatus.PARTIALLY_VERIFIED,
    EvidenceStatus.UNVERIFIED: DecisionStatus.UNVERIFIED,
    EvidenceStatus.HISTORICAL: DecisionStatus.HISTORICAL,
    EvidenceStatus.CONFLICTING: DecisionStatus.CONFLICTING,
}


def check_intake(question: Question) -> list[str]:
    """Rapportera saknade kritiska falt (tom lista = godkand intake)."""
    missing = [f for f in CRITICAL_INTAKE_FIELDS if not getattr(question, f, None)]
    context = question.context or {}
    if not context.get("situation") and not context.get("domain"):
        missing = [*missing, "context.situation|domain"]
    return missing


class PipelineResult:
    """Resultat fran run_pipeline: beslut + audit-spar."""

    __slots__ = ("decision", "audit")

    def __init__(self, decision: CouncilDecision, audit: AuditTrail) -> None:
        self.decision = decision
        self.audit = audit


def _decision_id(question_id: str, route: Sequence[str]) -> str:
    from kma.sources.utils import compute_checksum

    digest = compute_checksum({"question": question_id, "route": sorted(route)})
    return f"DEC-{digest[:12]}"


def _by_agent(contributions: Iterable[AgentContribution]) -> dict[str, AgentContribution]:
    by_agent: dict[str, AgentContribution] = {}
    for item in contributions:
        if item.agent_id in by_agent:
            raise PipelineError(f"dubbelt bidrag fran agent: {item.agent_id}")
        by_agent[item.agent_id] = item
    return by_agent
