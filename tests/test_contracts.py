"""KMA-004 Agent Contracts — tester för kontraktsfilerna och validatorn.

Innehåll testas via stabila rubriker och textankare, inte löptext.
"""
import re
import unittest
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
AGENTS = (
    "CHAIR", "AFS", "SAM", "OSA", "BYGG",
    "RISK", "PRAKTIK", "REVISION", "REDTEAM", "RESEARCH",
)

# Arkitekturens §4 Contract-fält (KMA_ARCHITECTURE.md §4).
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

# Notions nio kompletterande kontraktsområden -> stabila rubriker i filerna.
# inputs/outputs/escalation redovisas via §4-fälten (inputs, outputs,
# escalation_criteria) och reds i validatorns §4-loop; övriga egna rubriker.
COMPLEMENTARY_AREAS = (
    ("mission", "##", "mission"),
    ("scope", "##", "scope"),
    ("non-scope", "##", "non-scope"),
    ("inputs", "##", "inputs"),
    ("outputs", "##", "outputs"),
    ("evidence requirements", "###", "Evidence requirements"),
    ("confidence rules", "###", "Confidence rules"),
    ("escalation", "##", "escalation_criteria"),
    ("disagreement rules", "###", "Disagreement rules"),
)

# Det gemensamma outputkontraktet (Notion sida 01 och 04).
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

# Obligatoriska universalförbud i alla tio kontrakten (KMA-004 uppdrag §3).
UNIVERSAL_PROHIBITIONS = (
    "Får inte presentera obestyrkta regulatoriska påståenden som verifierade.",
    "Får inte kringgå KMA-003:s evidensregler (Evidence Engine).",
    "Får inte behandla historisk information som automatiskt gällande rätt.",
)

# Obligatoriska agentregler som textankare (Notion sida 04 + uppdraget).
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


def parse_contract(text):
    """Returnera {rubrik: innehåll} för ## och ### -nivåer."""
    sections = {}
    current = None
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


def validate_contract(text, name):
    """Deterministisk validering: tydlig, stabil felmeddelandelista i fast ordning."""
    errors = []
    sections = parse_contract(text)

    # §4-fält: saknade eller tomma sektioner.
    for field in SECTION4_FIELDS:
        if field not in sections:
            errors.append(f"{name}: saknad sektion '## {field}'")
        elif not sections[field]:
            errors.append(f"{name}: tom sektion '## {field}'")

    # Notions kompletterande områden med egna rubriker (ej §4-fälten).
    for _label, prefix, heading in COMPLEMENTARY_AREAS:
        if prefix == "##" and heading in SECTION4_FIELDS:
            continue  # reds av §4-loopen ovan
        if heading not in sections:
            errors.append(f"{name}: saknad sektion '{prefix} {heading}'")
        elif not sections[heading]:
            errors.append(f"{name}: tom sektion '{prefix} {heading}'")

    # Gemensamt output_schema: samtliga tio obligatoriska nycklar med kravtext.
    output_text = sections.get("output_schema", "")
    pairs = dict(re.findall(r"^- \*\*([a-z_]+):\*\*\s*(.+)$", output_text, flags=re.MULTILINE))
    for key in OUTPUT_KEYS:
        if key not in pairs:
            errors.append(f"{name}: output_schema saknar obligatorisk nyckel '{key}'")

    # Universalförbud i prohibitions.
    if "prohibitions" in sections:
        prohibitions = sections["prohibitions"]
        for line in UNIVERSAL_PROHIBITIONS:
            if line not in prohibitions:
                errors.append(f"{name}: saknar obligatoriskt förbud: '{line}'")

    return errors


def remove_section(text, heading):
    """Ta bort en ## -sektion inklusive innehåll (för negativa tester)."""
    out, skip = [], False
    for line in text.splitlines():
        if not skip and line.startswith("## ") and line[3:].strip() == heading:
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


def empty_section(text, heading):
    """Behåll rubriken men töm sektionens innehåll (för negativa tester)."""
    out, skip = [], False
    for line in text.splitlines():
        if not skip and line.startswith("## ") and line[3:].strip() == heading:
            out.append(line)
            skip = True
            continue
        if skip and line.startswith("#"):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


def remove_line_containing(text, needle):
    """Ta bort första raden som innehåller needle (för negativa tester)."""
    out, removed = [], False
    for line in text.splitlines():
        if not removed and needle in line:
            removed = True
            continue
        out.append(line)
    return "\n".join(out)


class ContractTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {}
        for aid in AGENTS:
            path = AGENTS_DIR / f"{aid}.md"
            cls.texts[aid] = path.read_text(encoding="utf-8")


class TestContractFilesExist(ContractTestCase):
    def test_all_ten_contracts_exist(self):
        expected = sorted(f"{aid}.md" for aid in AGENTS)
        actual = sorted(p.name for p in AGENTS_DIR.glob("*.md"))
        self.assertEqual(actual, expected)

    def test_no_unexpected_files_in_agents_dir(self):
        actual = sorted(p.name for p in AGENTS_DIR.iterdir())
        self.assertEqual(actual, sorted(f"{aid}.md" for aid in AGENTS))


class TestContractStructure(ContractTestCase):
    def test_section4_fields_present_and_nonempty(self):
        for aid, text in self.texts.items():
            sections = parse_contract(text)
            for field in SECTION4_FIELDS:
                with self.subTest(agent=aid, field=field):
                    self.assertIn(field, sections, f"{aid}: saknad sektion '## {field}'")
                    self.assertTrue(
                        sections[field].strip(), f"{aid}: tom sektion '## {field}'"
                    )

    def test_complementary_areas_documented(self):
        for aid, text in self.texts.items():
            sections = parse_contract(text)
            for label, prefix, heading in COMPLEMENTARY_AREAS:
                with self.subTest(agent=aid, area=label):
                    self.assertIn(
                        heading, sections, f"{aid}: saknad sektion '{prefix} {heading}'"
                    )
                    self.assertTrue(
                        sections[heading].strip(),
                        f"{aid}: tom sektion '{prefix} {heading}'",
                    )

    def test_output_schema_contains_all_ten_keys(self):
        for aid, text in self.texts.items():
            sections = parse_contract(text)
            pairs = dict(
                re.findall(
                    r"^- \*\*([a-z_]+):\*\*\s*(.+)$",
                    sections["output_schema"],
                    flags=re.MULTILINE,
                )
            )
            for key in OUTPUT_KEYS:
                with self.subTest(agent=aid, key=key):
                    self.assertIn(key, pairs, f"{aid}: output_schema saknar '{key}'")
                    self.assertTrue(pairs[key].strip(), f"{aid}: tomt krav för '{key}'")

    def test_output_schema_identical_across_contracts(self):
        parsed = {}
        for aid, text in self.texts.items():
            sections = parse_contract(text)
            parsed[aid] = dict(
                re.findall(
                    r"^- \*\*([a-z_]+):\*\*\s*(.+)$",
                    sections["output_schema"],
                    flags=re.MULTILINE,
                )
            )
        reference = parsed["CHAIR"]
        for aid, pairs in parsed.items():
            self.assertEqual(pairs, reference, f"{aid}: avvikande gemensamt output_schema")


class TestMandatoryAgentRules(ContractTestCase):
    def test_universal_prohibitions_in_all_contracts(self):
        for aid, text in self.texts.items():
            prohibitions = parse_contract(text).get("prohibitions", "")
            for line in UNIVERSAL_PROHIBITIONS:
                with self.subTest(agent=aid, prohibition=line):
                    self.assertIn(line, prohibitions, f"{aid}: saknar förbud: '{line}'")

    def test_agent_specific_rule_anchors(self):
        for aid, anchors in AGENT_RULE_ANCHORS.items():
            text = self.texts[aid]
            for anchor in anchors:
                with self.subTest(agent=aid, anchor=anchor):
                    self.assertIn(anchor, text, f"{aid}: saknar obligatorisk regel: '{anchor}'")


class TestValidator(ContractTestCase):
    def test_validator_accepts_all_real_contracts(self):
        for aid, text in self.texts.items():
            self.assertEqual(validate_contract(text, aid), [], f"{aid}: oväntade fel")

    def test_validator_rejects_missing_section(self):
        broken = remove_section(self.texts["CHAIR"], "inputs")
        self.assertEqual(
            validate_contract(broken, "CHAIR.md"),
            ["CHAIR.md: saknad sektion '## inputs'"],
        )

    def test_validator_rejects_empty_section(self):
        broken = empty_section(self.texts["CHAIR"], "role")
        self.assertEqual(
            validate_contract(broken, "CHAIR.md"),
            ["CHAIR.md: tom sektion '## role'"],
        )

    def test_validator_rejects_missing_output_key(self):
        broken = remove_line_containing(self.texts["CHAIR"], "- **risks:**")
        self.assertEqual(
            validate_contract(broken, "CHAIR.md"),
            ["CHAIR.md: output_schema saknar obligatorisk nyckel 'risks'"],
        )

    def test_validator_rejects_missing_universal_prohibition(self):
        broken = remove_line_containing(self.texts["CHAIR"], UNIVERSAL_PROHIBITIONS[0])
        self.assertEqual(
            validate_contract(broken, "CHAIR.md"),
            ["CHAIR.md: saknar obligatoriskt förbud: '" + UNIVERSAL_PROHIBITIONS[0] + "'"],
        )

    def test_validator_rejects_missing_subsection(self):
        broken = remove_line_containing(self.texts["CHAIR"], "### Confidence rules")
        # Rubriken borttagen -> hela Confidence rules-innehållet hamnar i
        # evidence_policy; delsektionen saknas alltså.
        errors = validate_contract(broken, "CHAIR.md")
        self.assertIn("CHAIR.md: saknad sektion '### Confidence rules'", errors)


if __name__ == "__main__":
    unittest.main()
