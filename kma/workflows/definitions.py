"""KMA Council - Workflows, definitioner A-C (KMA-006, steg A).

Workflows som data: varje workflow har exakt sju falt (sida 05):
required_intake, optional_intake, agent_route, evidence_policy,
output_schema, completion_criteria, escalation_criteria.
Inga regulatoriska sakpastaenden har (AD-1, §8). Del 2 lagger till D-G.
"""
from __future__ import annotations

from .errors import UnknownWorkflowError

__all__ = [
    "COMMON_OUTPUT",
    "COMPLETION_BASE",
    "ESCALATION_BASE",
    "EVIDENCE_POLICY_BASE",
    "REQUIRED_FIELDS",
    "WORKFLOWS",
    "get_workflow",
    "validate_definitions",
]

REQUIRED_FIELDS = (
    "required_intake",
    "optional_intake",
    "agent_route",
    "evidence_policy",
    "output_schema",
    "completion_criteria",
    "escalation_criteria",
)

# Gemensam output (§8, sida 03): elva punkter. Motorn mappar dessa som en
# vy over CouncilDecision; falt utan strukturerad motpart markeras
# uttryckligen i stallet for att gissas.
COMMON_OUTPUT = (
    "bedomning",
    "regelstod",
    "risker",
    "saknade_uppgifter",
    "atgarder",
    "ansvar",
    "dokumentation",
    "kontroller",
    "osakerheter",
    "kallor",
    "nasta_steg",
)

# Ateranvand dokumenterad policy (§6-gaten + AD-1/AD-2). Inga nya
# evidenskrav hitas pa; texten refererar endast befintliga regler.
EVIDENCE_POLICY_BASE = (
    "KMA-003 EvidenceEngine ar ensam auktoritet for EvidenceStatus (§6). "
    "VERIFIED kraver niva-1/2-kalla, aktuell version, exakt locator, "
    "hamtad text mot current snapshot (snapshot_ref obligatorisk). "
    "Niva 4 bar aldrig ensam ett regelclaim (AD-2); niva 3 bar aldrig "
    "foreskriftstext. AFS-referenser kommer endast fran registret; "
    "gissad paragraf ar ett valideringsfel (AD-3). Historik markeras "
    "HISTORICAL och blir aldrig aktuell regel. Alla regulatoriska "
    "pastaenden kraver evidence_refs (AD-1)."
)

COMPLETION_BASE = (
    "Komplett required intake; engine-validerad status; redovisade "
    "konflikter och dissent; REDTEAM/REVISION-fynd fore syntes dar "
    "routade; inga unsupported claims."
)

ESCALATION_BASE = (
    "INSUFFICIENT_EVIDENCE vid saknad kritisk information; "
    "CONFLICTING_EVIDENCE vid slutsatspaverkande konflikt; eskalera till "
    "manuell specialistbedomning vid okand currentness, okand fraga "
    "eller route som ej kan motiveras av §7."
)

WORKFLOWS: dict[str, dict] = {
    "A": {
        "id": "A",
        "name": "Regelkontroll",
        "required_intake": ("situation", "verksamhet", "arbetsmoment", "roller", "geo"),
        "optional_intake": ("utrustning", "tidpunkt", "tidigare_bedomning"),
        "agent_route": ("AFS", "RESEARCH"),
        "route_basis": "§7 AFS-fraga till AFS + RESEARCH.",
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": (
            "tillampliga_regler",
            "exakt_kalla",
            "krav",
            "ej_tillampliga_regler",
            "verifieringsbehov",
            *COMMON_OUTPUT,
        ),
        "completion_criteria": COMPLETION_BASE,
        "escalation_criteria": ESCALATION_BASE,
    },
    "B": {
        "id": "B",
        "name": "Riskbedomning",
        "required_intake": ("situation", "verksamhet", "faror"),
        "optional_intake": ("befintliga_skydd", "arbetsmoment", "roller", "geo", "deadline"),
        "agent_route": ("RISK", "SAM", "RESEARCH"),
        "route_basis": (
            "§7 incident-raden (RISK + SAM + REVISION + RESEARCH) och "
            "bygg-raden (BYGG + AFS + SAM + RISK + RESEARCH) innehaller "
            "bada RISK + SAM + RESEARCH; minsta tillrackliga rad utan "
            "REVISION da ingen incident utretts."
        ),
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": (
            "faror",
            "risker",
            "befintliga_skydd",
            "ytterligare_atgarder",
            "ansvar",
            "deadline",
            "kvarvarande_risk",
            "kontrollpunkter",
            *COMMON_OUTPUT,
        ),
        "completion_criteria": COMPLETION_BASE,
        "escalation_criteria": ESCALATION_BASE,
    },
    "C": {
        "id": "C",
        "name": "Produktionsstart",
        "required_intake": ("situation", "verksamhet", "organisation"),
        "optional_intake": (
            "riskbedomningar",
            "arbetsberedningar",
            "kompetens",
            "introduktion",
            "utrustning",
            "skydd",
            "entreprenorsgranssnitt",
            "dokumentation",
            "uppfoljning",
            "oppna_blockerare",
        ),
        "agent_route": ("BYGG", "AFS", "SAM", "RISK", "RESEARCH"),
        "route_basis": "§7 bygg/anlaggning till BYGG + AFS + SAM + RISK + RESEARCH.",
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": (
            "organisation_ansvar",
            "riskbedomningar",
            "arbetsberedningar",
            "kompetens",
            "introduktion",
            "utrustning",
            "skydd",
            "entreprenorsgranssnitt",
            "dokumentation",
            "uppfoljning",
            "oppna_blockerare",
            *COMMON_OUTPUT,
        ),
        "completion_criteria": (
            COMPLETION_BASE + " Oppna blockerare redovisas explicit; "
            "ofullstandig readiness ger ej VERIFIED."
        ),
        "escalation_criteria": ESCALATION_BASE,
    },
    "D": {
        "id": "D",
        "name": "TillbudOlycka",
        "required_intake": ("situation", "verksamhet", "handelsebeskrivning", "tidpunkt"),
        "optional_intake": ("skadade", "vittnen", "omedelbara_atgarder", "arbetsmoment", "roller", "geo"),
        "agent_route": ("RISK", "SAM", "REVISION", "RESEARCH"),
        "route_basis": "§7 incident till RISK + SAM + REVISION + RESEARCH.",
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": (
            "fakta_vs_antaganden",
            "omedelbara_atgarder",
            "mojliga_bakomliggande_orsaker",
            "regel_rapporteringsfragor",
            "utredningsplan",
            "korrigerande_preventiva_atgarder",
            "uppfoljning",
            *COMMON_OUTPUT,
        ),
        "completion_criteria": (
            COMPLETION_BASE + " Fakta skiljs fran antaganden; "
            "orsaksanalys markeras som mojlig, ej faststalld."
        ),
        "escalation_criteria": ESCALATION_BASE,
    },
    "E": {
        "id": "E",
        "name": "Inspektionsberedskap",
        "required_intake": ("situation", "verksamhet", "granskningsomrade"),
        "optional_intake": ("dokumentunderlag", "arbetsmoment", "roller", "tidigare_brister", "geo"),
        "agent_route": ("REVISION", "AFS", "PRAKTIK", "RESEARCH"),
        "route_basis": "§7 inspektion/dokumentgranskning till REVISION + AFS + PRAKTIK + RESEARCH.",
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": (
            "inspektorsfragor",
            "bevisbegaran",
            "luckor",
            "prioriterade_brister",
            "dokumentbrist_vs_faktisk_risk",
            *COMMON_OUTPUT,
        ),
        "completion_criteria": (
            COMPLETION_BASE + " Dokumentbrist skiljs fran faktisk risk; "
            "varje brist prioriteras efter allvarlighet."
        ),
        "escalation_criteria": ESCALATION_BASE,
    },
    "F": {
        "id": "F",
        "name": "Dokumentgranskning",
        "required_intake": ("situation", "verksamhet", "dokumentunderlag"),
        "optional_intake": ("granskningsomrade", "arbetsmoment", "roller", "tidigare_bedomning"),
        "agent_route": ("REVISION", "AFS", "PRAKTIK", "RESEARCH"),
        "route_basis": "§7 inspektion/dokumentgranskning till REVISION + AFS + PRAKTIK + RESEARCH.",
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": (
            "struktur",
            "regelstod",
            "motsagelser",
            "saknade_delar",
            "verklighetsbeskrivning",
            *COMMON_OUTPUT,
        ),
        "completion_criteria": (
            COMPLETION_BASE + " Komplett dokument utan verklig risk flaggas; "
            "motsagelser redovisas som konflikt."
        ),
        "escalation_criteria": ESCALATION_BASE,
    },
    "G": {
        "id": "G",
        "name": "GenerellKMAFraga",
        "required_intake": ("situation", "fraga"),
        "optional_intake": ("verksamhet", "arbetsmoment", "roller", "geo", "expert_hint"),
        "agent_route": ("AFS", "RESEARCH"),
        "route_basis": (
            "§7 generell fraga till relevanta experter + source verification; "
            "minsta rad AFS + RESEARCH. expert_hint (optional intake) kan "
            "begransa eller byta experter via validerad route-hint."
        ),
        "evidence_policy": EVIDENCE_POLICY_BASE,
        "output_schema": COMMON_OUTPUT,
        "completion_criteria": COMPLETION_BASE,
        "escalation_criteria": ESCALATION_BASE,
    },
}


def get_workflow(workflow_id: str) -> dict:
    """Hamta en workflowdefinition via explicit id; okant id eskalerar."""
    try:
        return WORKFLOWS[workflow_id]
    except KeyError:
        raise UnknownWorkflowError(
            f"okant workflow-id: {workflow_id!r} (giltiga: {sorted(WORKFLOWS)})"
        ) from None


def validate_definitions() -> list[str]:
    """Validera att alla workflows har exakt de sju obligatoriska falten."""
    errors: list[str] = []
    for wid in sorted(WORKFLOWS):
        spec = WORKFLOWS[wid]
        for field in REQUIRED_FIELDS:
            if field not in spec:
                errors.append(f"{wid}: saknar falt {field!r}")
            elif not spec[field]:
                errors.append(f"{wid}: tomt falt {field!r}")
        extra = [k for k in spec if k not in (*REQUIRED_FIELDS, "id", "name", "route_basis")]
        if extra:
            errors.append(f"{wid}: okanda falt {extra}")
    return errors
