"""KMA Council — Council Orchestration, kontraktslasare (KMA-005).

Tunn lasare som validerar befintliga Markdown-kontrakt i agents/ som data
(godkant beslut 2). Ateranvander rubrik- och ankarformatet fran
tests/test_contracts.py. Ingen ny typad kontraktsmodell (KMA-004 giltigt).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ContractLoadError

__all__ = [
    "AGENT_IDS",
    "SECTION4_FIELDS",
    "OUTPUT_KEYS",
    "UNIVERSAL_PROHIBITIONS",
    "AGENT_RULE_ANCHORS",
    "LoadedContract",
    "parse_sections",
    "validate_contract",
    "load_contract",
    "load_all_contracts",
]

AGENT_IDS = (
    "CHAIR", "AFS", "SAM", "OSA", "BYGG",
    "RISK", "PRAKTIK", "REVISION", "REDTEAM", "RESEARCH",
)

SECTION4_FIELDS = (
    "name",
    "role",
    "inputs",
    "outputs",
    "prohibitions",
    "evidence_policy",
    "output_schema",
    "completion_criteria",
    "escalation_criteria",
)

COMPLEMENTARY_HEADINGS = (
    "mission",
    "scope",
    "non-scope",
    "Evidence requirements",
    "Confidence rules",
    "Disagreement rules",
)

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

UNIVERSAL_PROHIBITIONS = (
    "Får inte presentera obestyrkta regulatoriska påståenden som verifierade.",
    "Får inte kringgå KMA-003:s evidensregler (Evidence Engine).",
    "Får inte behandla historisk information som automatiskt gällande rätt.",
)

AGENT_RULE_ANCHORS = {
    "CHAIR": ("Får inte själv tilldela eller uppgradera evidensstatus.",),
    "AFS": ("Får aldrig hitta på lagrum, föreskriftsreferenser, URL:er eller regulatoriska krav.",),
    "RESEARCH": (
        "Verifierar primärkällor och redovisar källa, version, currentness och osäkerhet enligt evidensmodellen.",
    ),
    "REDTEAM": (
        "Försöker falsifiera påståenden och identifierar motbevis, antaganden och svaga länkar.",
    ),
    "REVISION": (
        "Begär spårbara belägg för varje påstående och markerar otillräcklig evidens uttryckligen.",
    ),
}

AGENTS_DIRNAME = "agents"


@dataclass(frozen=True)
class LoadedContract:
    """Ett validerat kontrakt last som data (ej kod)."""

    agent_id: str
    sections: dict


def parse_sections(text: str) -> dict:
    """Returnera {rubrik: innehall} for ##- och ###-nivaer (samma format som testerna)."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            sections[current] = []
        elif line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif line.startswith("# "):
            current = None
        elif current is not None:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def validate_contract(text: str, name: str) -> list[str]:
    """Deterministisk validering: stabil felmeddelandelista i fast ordning."""
    import re

    errors: list[str] = []
    sections = parse_sections(text)
    for field in SECTION4_FIELDS:
        if field not in sections:
            errors.append(f"{name}: saknad sektion '## {field}'")
        elif not sections[field]:
            errors.append(f"{name}: tom sektion '## {field}'")
    for heading in COMPLEMENTARY_HEADINGS:
        prefix = "###" if heading[:1].isupper() else "##"
        if heading not in sections:
            errors.append(f"{name}: saknad sektion '{prefix} {heading}'")
        elif not sections[heading]:
            errors.append(f"{name}: tom sektion '{prefix} {heading}'")
    pairs = dict(
        re.findall(r"^- \*\*([a-z_]+):\*\*\s*(.+)$", sections.get("output_schema", ""), flags=re.MULTILINE)
    )
    for key in OUTPUT_KEYS:
        if key not in pairs:
            errors.append(f"{name}: output_schema saknar obligatorisk nyckel '{key}'")
    if "prohibitions" in sections:
        prohibitions = sections["prohibitions"]
        for line in UNIVERSAL_PROHIBITIONS:
            if line not in prohibitions:
                errors.append(f"{name}: saknar obligatoriskt forbud: '{line}'")
    for anchor in AGENT_RULE_ANCHORS.get(name, ()):
        if anchor not in text:
            errors.append(f"{name}: saknar obligatorisk agentregel: '{anchor}'")
    return errors


def _agents_dir(base: Path | None = None) -> Path:
    if base is not None:
        return Path(base)
    here = Path(__file__).resolve()
    for parent in (here.parent.parent.parent, here.parent.parent, here.parent):
        candidate = parent / AGENTS_DIRNAME
        if candidate.is_dir():
            return candidate
    return here.parent.parent.parent / AGENTS_DIRNAME


def load_contract(agent_id: str, base: Path | None = None) -> LoadedContract:
    """Las och validera ett kontrakt; fel ger ContractLoadError med deterministiskt meddelande."""
    if agent_id not in AGENT_IDS:
        raise ContractLoadError(f"okand agent: {agent_id!r}")
    path = _agents_dir(base) / f"{agent_id}.md"
    if not path.is_file():
        raise ContractLoadError(f"{agent_id}: kontrakt saknas ({path})")
    text = path.read_text(encoding="utf-8")
    errors = validate_contract(text, agent_id)
    if errors:
        raise ContractLoadError("; ".join(errors))
    return LoadedContract(agent_id=agent_id, sections=parse_sections(text))


def load_all_contracts(base: Path | None = None) -> dict[str, LoadedContract]:
    """Las och validera samtliga tio kontrakt i fast ordning."""
    return {aid: load_contract(aid, base) for aid in AGENT_IDS}
