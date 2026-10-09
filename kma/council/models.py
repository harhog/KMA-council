"""KMA Council — Council Orchestration, typade modeller (KMA-005).

Question, AgentContribution, CouncilDecision och Conflict som data.
Ingen separat Claim-modell: pastaenden baras som strangen claim_supported
med obligatoriska evidence_refs (godkant beslut 1).
Inga regulatoriska sakpastaenden i denna modul (AD-1).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "AgentContribution",
    "AuditEvent",
    "AuditTrail",
    "Conflict",
    "CouncilDecision",
    "DecisionStatus",
    "OUTPUT_KEYS",
    "Question",
    "QuestionKind",
]

OUTPUT_KEYS = (
    "assessment",
    "applicable_requirements",
    "evidence_refs",
    "risks",
    "missing_information",
    "recommendation",
    "confidence",
    "assumptions",
    "dissent",
    "reflection",
)

AGENT_IDS = (
    "CHAIR", "AFS", "SAM", "OSA", "BYGG",
    "RISK", "PRAKTIK", "REVISION", "REDTEAM", "RESEARCH",
)


class QuestionKind(str, Enum):
    """Fragakategori som styr routing (sida 04 route-tabell)."""

    AFS_FRAGA = "afs-fraga"
    SAM = "sam"
    OSA = "osa"
    BYGG = "bygg"
    INCIDENT = "incident"
    FULL_REVIEW = "full-review"
    UNKNOWN = "unknown"


class DecisionStatus(str, Enum):
    """Orkestreringens beslutsstatus (godkant beslut 6).

    Hallen atskild fran EvidenceStatus (KMA-003): INSUFFICIENT_EVIDENCE
    och CONFLICTING_EVIDENCE tillhor orkestreringen, ej evidensgaten.
    VERIFIED far endast forekomma efter framgangsrik engine-validering.
    """

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    HISTORICAL = "HISTORICAL"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class Question(BaseModel):
    """Generisk frageintagning (godkant beslut 4, KMA-006 ager detaljer)."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    question_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    kind: QuestionKind = Field(QuestionKind.UNKNOWN)
    context: dict[str, Any] = Field(default_factory=dict)
    route_hint: list[str] = Field(default_factory=list)

    @field_validator("question_id", "text")
    @classmethod
    def _no_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("falt far inte vara blankt")
        return v.strip()

    @field_validator("route_hint", mode="before")
    @classmethod
    def _hint_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


class AgentContribution(BaseModel):
    """Ett injicerat agentbidrag enligt det gemensamma outputkontraktet.

    Bidrag injiceras som data; ingen LLM- eller agentkorning (beslut 3).
    Regulatoriska pastaenden kraver evidence_refs (AD-1).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    agent_id: str = Field(..., min_length=1)
    assessment: str = Field(..., min_length=1)
    applicable_requirements: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommendation: str = Field("", description="Rekommendation (tom tillaten).")
    confidence: float = Field(..., ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    dissent: str = Field("", description="Avvikande mening (tom tillaten).")
    reflection: str = Field("", description="Sjalvreflektion (tom tillaten).")

    @field_validator("agent_id")
    @classmethod
    def _known_agent(cls, v: str) -> str:
        v = (v or "").strip()
        if v not in AGENT_IDS:
            raise ValueError(f"okand agent: {v!r}")
        return v

    @model_validator(mode="after")
    def _requirements_need_evidence(self) -> "AgentContribution":
        if self.applicable_requirements and not self.evidence_refs:
            raise ValueError(
                "regulatoriska pastaenden kraver evidence_refs (AD-1)"
            )
        return self


class Conflict(BaseModel):
    """Redovisad oenighet: bevaras och redovisas, loses aldrig tyst."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    claim: str = Field(..., min_length=1)
    sides: list[str] = Field(..., min_length=2)
    agents: list[str] = Field(..., min_length=2)
    description: str = Field(..., min_length=1)
    affects_conclusion: bool = Field(True)
    resolved: bool = Field(False, description="Alltid False i KMA-005.")

    @model_validator(mode="after")
    def _never_resolved(cls, m: "Conflict") -> "Conflict":
        if m.resolved is not False:
            raise ValueError("konflikter far inte markeras losta i KMA-005")
        return m


class CouncilDecision(BaseModel):
    """Slutligt beslutsunderlag fran CHAIR-syntesen (steg 9+10+11)."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    decision_id: str = Field(..., min_length=1)
    question_id: str = Field(..., min_length=1)
    route: list[str] = Field(..., min_length=1)
    status: DecisionStatus = Field(...)
    assessment: str = Field(..., min_length=1)
    applicable_requirements: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommendation: str = Field("")
    confidence: float = Field(..., ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    dissent: str = Field("")
    reflection: str = Field("")
    conflicts: list[Conflict] = Field(default_factory=list)
    red_team_findings: list[str] = Field(default_factory=list)
    revision_findings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _status_consistency(self) -> "CouncilDecision":
        if self.status is DecisionStatus.INSUFFICIENT_EVIDENCE and not self.missing_information:
            raise ValueError("INSUFFICIENT_EVIDENCE kraver missing_information")
        if self.status is DecisionStatus.CONFLICTING_EVIDENCE and not self.conflicts:
            raise ValueError("CONFLICTING_EVIDENCE kraver redovisade konflikter")
        if self.applicable_requirements and not self.evidence_refs:
            raise ValueError("regulatoriska pastaenden kraver evidence_refs (AD-1)")
        return self


class AuditEvent(BaseModel):
    """En handelse i det minimala audit-sparet (godkant beslut 5)."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    seq: int = Field(..., ge=0)
    step: str = Field(..., min_length=1)
    detail: str = Field("")


class AuditTrail(BaseModel):
    """Deterministiskt audit-spar: ordnad handelselista, ingen klocka."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    question_id: str = Field(..., min_length=1)
    events: list[AuditEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ordered(cls, m: "AuditTrail") -> "AuditTrail":
        for i, e in enumerate(m.events):
            if e.seq != i:
                raise ValueError("audit-sparet maste vara ordnat 0..n utan luckor")
        return m

    def append(self, step: str, detail: str = "") -> "AuditTrail":
        return AuditTrail(
            question_id=self.question_id,
            events=[*self.events, AuditEvent(seq=len(self.events), step=step, detail=detail)],
        )
