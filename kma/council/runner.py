"""KMA Council - Council Orchestration runner del 1 (KMA-005).

Intake, routing, bidrag och konfliktdetektering. Del 2 fortsatt nedan.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from kma.evidence import Evidence, EvidenceEngine

from . import routing as _routing
from .contracts import load_contract
from .errors import IntakeError, PipelineError
from .models import (
    AgentContribution,
    Conflict,
    CouncilDecision,
    DecisionStatus,
    Question,
    QuestionKind,
)
from .pipeline import (
    _by_agent,
    _decision_id,
    AuditTrail,
    PipelineResult,
    check_intake,
)

__all__ = ["run_pipeline", "intake_question", "question_kind_from_text"]


def _open_pipeline(question: Question):
    audit = AuditTrail(question_id=question.question_id)
    audit = audit.append("intake", f"fraga {question.question_id} mottagen")
    audit = audit.append("classification", f"kind={question.kind.value}")
    return audit


def _gate_or_route(question: Question, audit: AuditTrail):
    missing = check_intake(question)
    if missing:
        audit = audit.append("missing_information_gate", "saknas: " + ", ".join(missing))
        decision = CouncilDecision(
            decision_id=_decision_id(question.question_id, ("CHAIR",)),
            question_id=question.question_id,
            route=["CHAIR"],
            status=DecisionStatus.INSUFFICIENT_EVIDENCE,
            assessment="Fragan kan inte analyseras: kritisk information saknas.",
            missing_information=list(missing),
            recommendation="Komplettera saknad information och kor fragan igen.",
            confidence=0.0,
            reflection="Intake-gaten stoppade analysen fore routing.",
        )
        audit = audit.append("final_output", "status=INSUFFICIENT_EVIDENCE")
        return None, decision, audit
    audit = audit.append("missing_information_gate", "godkand")
    route = list(_routing.route(question))
    audit = audit.append("expert_routing", "route=" + "+".join(route))
    return route, None, audit

def _collect(question, contributions, engine, evidences, audit, route, contracts_base):
    for agent_id in ("CHAIR", *route):
        load_contract(agent_id, contracts_base)
    audit = audit.append("contracts_validated", "kontrakt lasta som data")
    by_agent = _by_agent(contributions)
    absent = [m for m in route if m not in by_agent]
    if absent:
        raise PipelineError(f"saknade bidrag fran routade agenter: {absent}")
    ordered = sorted(by_agent.values(), key=lambda c: c.agent_id)
    audit = audit.append("parallel_analysis", "bidrag_ok")
    note = ""
    if "RESEARCH" in by_agent:
        note = "; ".join(by_agent["RESEARCH"].missing_information) or "ok"
    audit = audit.append("research_source_verification", note or "ej routad")
    pool = dict(evidences or {})
    referenced: list[Evidence] = []
    unknown_refs: list[str] = []
    for item in ordered:
        for ref in item.evidence_refs:
            ev = pool.get(ref)
            if ev is None:
                unknown_refs.append(f"{item.agent_id}:{ref}")
            elif ev not in referenced:
                referenced.append(ev)
    audit = audit.append("evidence_collected", f"{len(referenced)} evidenser")
    if unknown_refs:
        raise PipelineError(f"okanda evidence_refs: {unknown_refs}")
    return by_agent, ordered, referenced, audit


def _conflicts(engine, ordered, referenced, audit):
    conflicts: list[Conflict] = []
    for ec in engine.detect_conflicts(referenced):
        agents = sorted({c.agent_id for c in ordered if set(c.evidence_refs) & set(ec.evidence_ids)})
        fallback = sorted({c.agent_id for c in ordered})
        while len(fallback) < 2:
            fallback.append("CHAIR")
        conflicts.append(
            Conflict(
                claim=ec.claim_supported,
                sides=[f"{i}:{s.value}" for i, s in zip(ec.evidence_ids, ec.statuses)],
                agents=agents if len(agents) >= 2 else fallback,
                description="motstridiga statusar",
                affects_conclusion=True,
                resolved=False,
            )
        )
    dissents = [(c.agent_id, c.dissent) for c in ordered if c.dissent.strip()]
    if len(dissents) >= 2 and not conflicts:
        agents = sorted(a for a, _ in dissents)
        conflicts.append(
            Conflict(
                claim="; ".join(sorted({c.assessment for c in ordered})),
                sides=[f"{a}: {d}" for a, d in sorted(dissents)],
                agents=agents if len(agents) >= 2 else [agents[0], "CHAIR"],
                description="avvikande mening som paverkar slutsatsen",
                affects_conclusion=True,
                resolved=False,
            )
        )
    audit = audit.append("conflict_detection", f"{len(conflicts)} konflikter")
    return conflicts, dissents, audit



def _synthesise(question, by_agent, ordered, referenced, conflicts, dissents, audit, route, engine):
    from kma.evidence import EvidenceStatus as _ES
    from .pipeline import _EVIDENCE_TO_DECISION as _MAP

    red_findings: list[str] = []
    rev_findings: list[str] = []
    if "REDTEAM" in route:
        red = by_agent.get("REDTEAM")
        if red is None:
            raise PipelineError("REDTEAM routad men saknar bidrag")
        red_findings = [red.assessment, *red.risks, *red.missing_information]
    if "REVISION" in route:
        rev = by_agent.get("REVISION")
        if rev is None:
            raise PipelineError("REVISION routad men saknar bidrag")
        rev_findings = [rev.assessment, *rev.missing_information]
    audit = audit.append("red_team_review", "red+rev klara")
    chair_text = by_agent["CHAIR"].assessment if "CHAIR" in by_agent else ""
    parts = [c.assessment for c in ordered if c.agent_id != "CHAIR"]
    assessment = " ".join(p for p in [chair_text, *parts] if p) or "Ingen bedomning."
    applicable = sorted({r for c in ordered for r in c.applicable_requirements})
    refs = sorted({r for c in ordered for r in c.evidence_refs})
    audit = audit.append("chair_synthesis", f"krav={len(applicable)}; refs={len(refs)}")
    for req in applicable:
        if not [e for e in referenced if e.claim_supported == req]:
            raise PipelineError(f"pastaende utan evidens (AD-1): {req}")
    claim_status = engine.verify_claim(referenced) if referenced else _ES.UNVERIFIED
    status = _MAP[claim_status]
    audit = audit.append("evidence_validation", f"claim-status={claim_status.value}")
    missing_info = sorted({m for c in ordered for m in c.missing_information})
    if conflicts and any(c.affects_conclusion for c in conflicts):
        status = DecisionStatus.CONFLICTING_EVIDENCE
    if missing_info and status in (DecisionStatus.VERIFIED, DecisionStatus.PARTIALLY_VERIFIED):
        status = DecisionStatus.UNVERIFIED
    decision = CouncilDecision(
        decision_id=_decision_id(question.question_id, route),
        question_id=question.question_id,
        route=list(route),
        status=status,
        assessment=assessment,
        applicable_requirements=applicable,
        evidence_refs=refs,
        risks=sorted({r for c in ordered for r in c.risks}),
        missing_information=missing_info,
        recommendation=next((c.recommendation for c in ordered if c.recommendation), ""),
        confidence=min((c.confidence for c in ordered), default=0.0),
        assumptions=sorted({a for c in ordered for a in c.assumptions}),
        dissent="; ".join(f"{a}: {d}" for a, d in sorted(dissents)),
        reflection="Syntes av injicerade bidrag; status satt av EvidenceEngine.",
        conflicts=conflicts,
        red_team_findings=red_findings,
        revision_findings=rev_findings,
    )
    audit = audit.append("final_output", f"status={status.value}")
    return PipelineResult(decision, audit)


def run_pipeline(question, contributions, engine, evidences=None, *, contracts_base=None):
    audit = _open_pipeline(question)
    route, early, audit = _gate_or_route(question, audit)
    if early is not None:
        return PipelineResult(early, audit)
    by_agent, ordered, referenced, audit = _collect(
        question, contributions, engine, evidences, audit, route, contracts_base
    )
    conflicts, dissents, audit = _conflicts(engine, ordered, referenced, audit)
    return _synthesise(question, by_agent, ordered, referenced, conflicts, dissents, audit, route, engine)


def question_kind_from_text(text: str) -> QuestionKind:
    lowered = (text or "").lower()
    if any(w in lowered for w in ("afs", "foreskrift", "paragraf", "lagrum")):
        return QuestionKind.AFS_FRAGA
    if "osa" in lowered or "organisatorisk" in lowered:
        return QuestionKind.OSA
    if "bygg" in lowered or "entreprenor" in lowered:
        return QuestionKind.BYGG
    if "tillbud" in lowered or "olycka" in lowered or "incident" in lowered:
        return QuestionKind.INCIDENT
    if "sam" in lowered or "systematiskt arbetsmiljoarbete" in lowered:
        return QuestionKind.SAM
    if "full" in lowered and "review" in lowered:
        return QuestionKind.FULL_REVIEW
    return QuestionKind.UNKNOWN


def intake_question(question_id, text, context=None, route_hint=None) -> Question:
    if not text or not text.strip():
        raise IntakeError("fragan saknar text (kritisk information)")
    return Question(
        question_id=question_id,
        text=text,
        kind=question_kind_from_text(text),
        context=dict(context or {}),
        route_hint=list(route_hint or []),
    )
