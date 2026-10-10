"""KMA Council - Workflows, motor (KMA-006, steg B).

Tunn adapter över KMA-005:s deterministiska 11-stegspipeline. Workflow-logiken
ligger i: explicit workflow-id, required/optional intake-validering,
route-hint-validering och vy-mappning till den gemensamma 11-punkts-outputen.
Inga LLM, inget nätverk, inga domänpåståenden (AD-1, AD-4). Bevisförvaring
och -gate är EvidenceEngine:s ensam auktoritet: workfoljen uppgraderar aldrig
EvidenceStatus och inget beslut får bli VERIFIED utan engine-godkännande
inklusive snapshot_ref.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from kma.council import run_pipeline
from kma.council.models import (
    AuditTrail,
    CouncilDecision,
    DecisionStatus,
    Question,
    QuestionKind,
)
from kma.evidence import EvidenceEngine
from kma.evidence.models import Evidence
from kma.sources import SourceRegistry
from kma.workflows.definitions import (
    COMMON_OUTPUT,
    REQUIRED_FIELDS,
    WORKFLOWS,
    get_workflow,
    validate_definitions,
)

from .errors import (
    UnknownWorkflowError,
    WorkflowError,
    WorkflowIntakeError,
    WorkflowRouteError,
)

__all__ = [
    "WorkflowError",
    "UnknownWorkflowError",
    "WorkflowIntakeError",
    "WorkflowRouteError",
    "WorkflowResult",
    "select_workflow",
    "validate_intake",
    "validate_route",
    "build_question",
    "run_workflow",
]

# Vända projektion från CouncilDecision-fält till workflow output-schema.
# Fält utan dokumenterad motpart blir None (ej tilldelat, aldrig gissat).
_SCHEMA_FIELD_TO_DECISION: dict[str, str] = {
    "tillampliga_regler": "applicable_requirements",
    "exakt_kalla": "evidence_refs",
    "krav": "applicable_requirements",
    "ej_tillampliga_regler": "missing_information",
    "verifieringsbehov": "missing_information",
    "faror": "risks",
    "risker": "risks",
    "befintliga_skydd": "assumptions",
    "ytterligare_atgarder": "recommendation",
    "ansvar": "assumptions",
    "deadline": "assumptions",
    "kvarvarande_risk": "risks",
    "kontrollpunkter": "revision_findings",
    "inspektorsfragor": "assessment",
    "bevisbegaran": "missing_information",
    "luckor": "missing_information",
    "prioriterade_brister": "missing_information",
    "dokumentbrist_vs_faktisk_risk": "dissent",
}

@dataclass(frozen=True)
class WorkflowResult:
    """Ett verifierat workflow-resultat.

    output innehåller den valda workflow-specifika schemat + den gemensamma
    11-punkts-outputen från arkitekturen (§8, sida 03). Inga beslut fattas,
    inget bevis uppgraderas.
    """

    workflow_id: str
    question: Question
    decision: CouncilDecision
    audit: AuditTrail
    output: dict[str, Any]

# ---------------------------------------------------------------- step A --


def select_workflow(workflow_id: str) -> dict[str, Any]:
    """Hamta en workflowdefinition via explicit id; okant id eskalerar.

    Gissas aldrig (AD-4). Returnerar den osnabbt valda definitionen.
    """
    return get_workflow(workflow_id)


# ---------------------------------------------------------------- intake --


def validate_intake(
    workflow_id: str, intake: Mapping[str, Any]
) -> dict[str, Any]:
    """Validera en intake mot workflowns required/optional intakelycken.

    Obligatoriska nycklar måste finnas och vara icke-tomma. Obundna nycklar
    avvisas (ingen gissning, ingen fyllning). Returnerar rensat dict.
    """
    spec = select_workflow(workflow_id)
    required = set(spec["required_intake"])
    optional = set(spec["optional_intake"])
    errors: list[str] = []
    validated: dict[str, Any] = {}

    for key in sorted(required):
        if key not in intake:
            errors.append(f"saknar obligatorisk intakelycka: {key}")
        else:
            value = intake[key]
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"obligatorisk intakelycka {key} är tom")
            else:
                validated[key] = value

    for key, value in intake.items():
        if key in required:
            continue
        if key in optional:
            validated[key] = value
        else:
            errors.append(f"okänd intakelycka: {key}")

    if errors:
        raise WorkflowIntakeError("; ".join(errors))
    return validated


# ---------------------------------------------------------------- route --


def validate_route(
    workflow_id: str, route_hint: Sequence[str] | None
) -> tuple[str, ...]:
    """Validera en route-hint mot workflowns agentroute och FULL_COUNCIL.

    None/tyvt hint -> workflowns egna agentroute. Icke-tom hint måste vara en
    icke-tom delmängd av workflowns agentroute och alla agenter måste vara
    giltiga i FULL_COUNCIL (AD-4: gissas aldrig).
    """
    spec = select_workflow(workflow_id)
    allowed = spec["agent_route"]
    if route_hint is None:
        return tuple(allowed)

    hint = list(route_hint)
    if not hint:
        return tuple(allowed)

    invalid = [h for h in hint if h not in allowed]
    if invalid:
        raise WorkflowRouteError(
            f"agent {invalid!r} kan inte läggas till workflow {workflow_id!r} "
            f"(giltiga: {sorted(allowed)})"
        )
    return tuple(hint)


# ----------------------------------------------------------------- question --


def build_question(
    workflow_id: str,
    intake: Mapping[str, Any],
    *,
    route_hint: Sequence[str] | None = None,
) -> Question:
    """Bygg en Council Question från workflow-intake.

    Contexten rikas ut med councilets kritiska fält så att
    KMA-005:s intake-gate kan godkännas (text + situation/domain). Detta är
    en kompatibilitetsskydd för att workflow-intake ska kunna köras i
    befintlig pipeline (AD-1: ingen ny kritisk fält definieras här).
    """
    validated = validate_intake(workflow_id, intake)
    spec = select_workflow(workflow_id)
    context: dict[str, Any] = dict(validated)
    context["domain"] = f"workflow-{workflow_id}"  # council critical field

    return Question(
        question_id=f"wk-{workflow_id}",
        text=" ".join(
            [f"[{spec['name']}] {spec['id']}"]
            + [f"{k}={v}" for k, v in validated.items()]
        ),
        kind=QuestionKind.UNKNOWN,
        context=context,
        route_hint=list(validate_route(workflow_id, route_hint)),
    )


# --------------------------------------------------------------- vy-mappning --


def _map_common_output(decision: CouncilDecision) -> dict[str, Any]:
    """Mappa CouncilDecision till den gemensamma 11-punkts-outputen (§8).

    Projektioner (proxy). Beslutsfälten är källan; workflow-vyn är läsvänlig.
    """
    return {
        "bedomning": decision.assessment,
        "regelstod": decision.applicable_requirements,
        "risker": decision.risks,
        "saknade_uppgifter": decision.missing_information,
        "atgarder": decision.recommendation,
        "ansvar": decision.assumptions,
        "dokumentation": decision.red_team_findings,
        "kontroller": decision.revision_findings,
        "osakerheter": decision.dissent,
        "kallor": decision.evidence_refs,
        "nasta_steg": decision.recommendation or decision.missing_information,
    }


def _escalation_text(decision: CouncilDecision) -> str:
    """Short Escalation-sträng baserad på beslutsstatus."""
    if decision.status is DecisionStatus.INSUFFICIENT_EVIDENCE:
        return "ESKALERAR: otillräcklig evidens; saknas: " + ", ".join(
            decision.missing_information
        )
    if decision.status is DecisionStatus.CONFLICTING_EVIDENCE:
        return "ESKALERAR: slutsatspåverkande konflikt; se conflict.red_team"
    if decision.status is DecisionStatus.HISTORICAL:
        return "ESKALERAR: historisk evidens; aldrig aktuell regel."
    if decision.status is DecisionStatus.CONFLICTING:
        return "ESKALERAR: konfliktande evidens; se conflict.red_team"
    if decision.status is DecisionStatus.UNVERIFIED:
        return "OBS: evidens ej godkänd; beslut ej VERIFIED."
    return "ingen eskalering"


# --------------------------------------------------------------- run_workflow --


def run_workflow(
    workflow_id: str,
    intake: Mapping[str, Any],
    *,
    contributions: Sequence[Any] = (),
    council_engine: Any = None,
    evidences: Mapping[str, Evidence] | None = None,
    contracts_base: str | None = None,
    route_hint: Sequence[str] | None = None,
) -> WorkflowResult:
    """Kör en workflow som en tunn schablon över KMA-005:s run_pipeline.

    Args:
        council_engine: EvidenceEngine för gate. Om None skapas en tom
            (den kör endast detect_conflicts/verify_claim på bidragen).
        evidences: Evidensregister (inte återanvänt av workflow-lagret).

    Returnerar WorkflowResult med beslut, audit och workflow-vy av beslutet.
    Inga valideringsfel (WorkflowIntakeError/WorkflowRouteError) rapporteras
    som beslut - de är fel i anropet. Ett giltigt beslut med otillräcklig
    evidens får status UNVERIFIED/HISTORICAL/CONFLICTING_EVIDENCE.
    """
    workflow = select_workflow(workflow_id)
    validated = validate_intake(workflow_id, intake)
    route = validate_route(workflow_id, route_hint)
    question = build_question(workflow_id, validated, route_hint=route)

    engine = council_engine if council_engine is not None else EvidenceEngine(SourceRegistry())

    pipeline_result = run_pipeline(
        question,
        contributions,
        engine,
        evidences=evidences,
        contracts_base=contracts_base,
    )
    decision = pipeline_result.decision
    audit = pipeline_result.audit

    schema_output: dict[str, Any] = {}
    for field in workflow["output_schema"]:
        target = _SCHEMA_FIELD_TO_DECISION.get(field)
        if target is None:
            schema_output[field] = None  # ej tilldelat, aldrig gissat
        else:
            schema_output[field] = getattr(decision, target, None)

    common_output = _map_common_output(decision)
    output: dict[str, Any] = {
        **schema_output,
        **common_output,
        "eskalering": _escalation_text(decision),
        "_audit_steps": list(audit.events),
    }
    return WorkflowResult(
        workflow_id=workflow_id,
        question=question,
        decision=decision,
        audit=audit,
        output=output,
    )

