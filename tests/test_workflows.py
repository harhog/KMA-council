"""KMA-006 Workflows - tester: A-G-definitioner, intake/route-validering, motor.

Positivt + negativt test per workflow A-G. Evidens-, konflikt-, dissent- och
red-team/REVISION-grindar delegeras till KMA-005 EvidenceEngine/run_pipeline
och verifieras genom tunn adapter (ingen gate kringgas, inget gissas).
"""
import unittest
from datetime import date, datetime

from kma.council import AgentContribution, QuestionKind
from kma.workflows import (
    REQUIRED_FIELDS,
    WORKFLOWS,
    WorkflowIntakeError,
    WorkflowRouteError,
    UnknownWorkflowError,
    get_workflow,
    run_workflow,
    select_workflow,
    validate_definitions,
    validate_intake,
    validate_route,
)

AS_OF = date(2026, 10, 8)
RETRIEVED_AT = datetime(2026, 9, 1, 12, 0, 0)
CLAIM = "Skyddsatgarder kravs vid fallrisk"
QUOTE = "Arbetsgivaren ska vidta de atgarder som behovs."
CTX = {"situation": "arbete pa hojd med fallrisk"}

ALL_IDS = ("A", "B", "C", "D", "E", "F", "G")


def make_engine():
    """Samma fixture-monster som KMA-005: current + historisk kalla."""
    from kma.evidence import EvidenceEngine
    from kma.sources import (
        AuthorityLevel,
        Currentness,
        Source,
        SourceRegistry,
        SourceType,
        SourceVersion,
    )

    registry = SourceRegistry()
    registry.register(Source(
        source_id="AFS2023:1", publisher="Arbetsmiljoverket", title="AFS 2023:1",
        source_type=SourceType.AFS, canonical_url="https://example.com/afs/AFS2023:1",
        authority_level=AuthorityLevel.PRIMAR_LAG, version_status=Currentness.CURRENT))
    registry.register(Source(
        source_id="HIST:1", publisher="Arbetsmiljoverket", title="Historisk foreskrift",
        source_type=SourceType.AFS, canonical_url="https://example.com/afs/HIST:1",
        authority_level=AuthorityLevel.PRIMAR_LAG, version_status=Currentness.HISTORICAL))
    engine = EvidenceEngine(registry)
    engine.register_version(SourceVersion(
        source_id="AFS2023:1", version="2024:1", effective_from=date(2025, 1, 1),
        snapshot_ref="data/snapshots/2026-01-05"))
    engine.register_version(SourceVersion(
        source_id="HIST:1", version="2020:1", effective_from=date(2020, 1, 1),
        effective_to=date(2022, 12, 31), snapshot_ref="data/snapshots/2022-12-31"))
    return engine


def build_evidence(engine, source_id, version, claim=CLAIM, locator="kapitel 5 paragraf 3"):
    return engine.build(
        source_id=source_id, version=version, locator=locator, claim_supported=claim,
        as_of=AS_OF, effective_date=date(2026, 6, 1),
        retrieved_at=RETRIEVED_AT, quote_or_excerpt=QUOTE)


def contrib(agent_id, **overrides):
    kwargs = dict(agent_id=agent_id, assessment=f"Bedomning fran {agent_id}.", confidence=0.8)
    kwargs.update(overrides)
    return AgentContribution(**kwargs)


# Minimalt giltig required-intake per workflow (alla required-nycklar, icke-tomma).
REQUIRED_INTAKE = {
    "A": {"situation": "arbete pa hojd", "verksamhet": "bygg",
          "arbetsmoment": "stalmontage", "roller": "montor", "geo": "Sverige"},
    "B": {"situation": "manuell lyft", "verksamhet": "lager", "faror": "tunga lyft"},
    "C": {"situation": "oppnar linje", "verksamhet": "tillverkning", "organisation": "ABB"},
    "D": {"situation": "olycka i trappa", "verksamhet": "kontor",
          "handelsebeskrivning": "person rullade i trappa", "tidpunkt": "2026-09-01"},
    "E": {"situation": "inspektion nara", "verksamhet": "bygg",
          "granskningsomrade": "fallskydd"},
    "F": {"situation": "granskning av dokument", "verksamhet": "bygg",
          "dokumentunderlag": "AI-plan"},
    "G": {"situation": "fragar om regler", "fraga": "galler AFS for stegar?"},
}


def full_contributions(route):
    """Ett bidrag per routad agent (pipelinen kraver alla routade agenter)."""
    return [contrib(agent) for agent in route]


class TestDefinitionsStructure(unittest.TestCase):
    def test_all_workflows_present(self):
        self.assertEqual(set(WORKFLOWS), set(ALL_IDS))

    def test_each_workflow_has_exactly_required_fields(self):
        for wid in ALL_IDS:
            spec = WORKFLOWS[wid]
            for field in REQUIRED_FIELDS:
                self.assertIn(field, spec, f"{wid} saknar falt {field}")
                self.assertTrue(spec[field], f"{wid} tomt falt {field}")

    def test_validate_definitions_reports_no_errors(self):
        self.assertEqual(validate_definitions(), [])

    def test_get_workflow_unknown_raises(self):
        with self.assertRaises(UnknownWorkflowError):
            get_workflow("Z")

    def test_select_workflow_returns_definition(self):
        self.assertEqual(select_workflow("A")["name"], "Regelkontroll")


class TestValidateRoute(unittest.TestCase):
    def test_none_hint_returns_workflow_route(self):
        for wid in ALL_IDS:
            allowed = tuple(WORKFLOWS[wid]["agent_route"])
            self.assertEqual(validate_route(wid, None), allowed)

    def test_empty_hint_returns_workflow_route(self):
        self.assertEqual(validate_route("A", []), tuple(WORKFLOWS["A"]["agent_route"]))

    def test_valid_subset_accepted(self):
        self.assertEqual(validate_route("A", ["RESEARCH"]), ("RESEARCH",))

    def test_agent_outside_workflow_route_rejected(self):
        with self.assertRaises(WorkflowRouteError):
            validate_route("G", ["REDTEAM"])

    def test_unknown_agent_rejected(self):
        with self.assertRaises(WorkflowRouteError):
            validate_route("A", ["NOBODY"])


class TestValidateIntake(unittest.TestCase):
    def test_valid_required_intake_accepted(self):
        for wid in ALL_IDS:
            validated = validate_intake(wid, REQUIRED_INTAKE[wid])
            for key in WORKFLOWS[wid]["required_intake"]:
                self.assertIn(key, validated)

    def test_missing_required_key_rejected(self):
        intake = dict(REQUIRED_INTAKE["A"])
        del intake["situation"]
        with self.assertRaises(WorkflowIntakeError):
            validate_intake("A", intake)

    def test_empty_required_value_rejected(self):
        intake = dict(REQUIRED_INTAKE["A"])
        intake["situation"] = "   "
        with self.assertRaises(WorkflowIntakeError):
            validate_intake("A", intake)

    def test_unknown_key_rejected(self):
        intake = dict(REQUIRED_INTAKE["A"])
        intake["okand_nyckel"] = "v"
        with self.assertRaises(WorkflowIntakeError):
            validate_intake("A", intake)

    def test_optional_key_kept(self):
        intake = dict(REQUIRED_INTAKE["A"])
        intake["utrustning"] = "selar"
        validated = validate_intake("A", intake)
        self.assertEqual(validated["utrustning"], "selar")



class TestRunWorkflowPositive(unittest.TestCase):
    """Positivt test per workflow A-G: kors pipelinen, output innehaller schema."""

    def test_each_workflow_runs_and_maps_output(self):
        for wid in ALL_IDS:
            with self.subTest(workflow=wid):
                route = tuple(WORKFLOWS[wid]["agent_route"])
                res = run_workflow(
                    wid, REQUIRED_INTAKE[wid],
                    contributions=full_contributions(route))
                self.assertEqual(res.workflow_id, wid)
                self.assertEqual(res.question.kind, QuestionKind.UNKNOWN)
                # Output innehaller hela workflow-schemat + gemensamma 11 punkter.
                for field in WORKFLOWS[wid]["output_schema"]:
                    self.assertIn(field, res.output)
                # Audit-spar fran KMA-005 pipelinen bevaras i vyn.
                self.assertIn("_audit_steps", res.output)
                steps = [e.step for e in res.audit.events]
                self.assertIn("final_output", steps)

    def test_intake_mapped_into_question_context(self):
        res = run_workflow("A", REQUIRED_INTAKE["A"],
                           contributions=full_contributions(("AFS", "RESEARCH")))
        self.assertEqual(res.question.context["domain"], "workflow-A")
        self.assertEqual(res.question.context["verksamhet"], "bygg")

    def test_unknown_workflow_raises(self):
        with self.assertRaises(UnknownWorkflowError):
            run_workflow("Z", {})

    def test_missing_intake_raises_not_decision(self):
        # Saknad obligatorisk intake far aldrig gissas: valideringsfel, inte beslut.
        with self.assertRaises(WorkflowIntakeError):
            run_workflow("A", {"situation": "x"})


class TestEvidenceGatePreserved(unittest.TestCase):
    """Grindarna kringgas inte: insufficient/historisk evidens blir ej VERIFIED."""

    def test_no_evidence_never_verified(self):
        res = run_workflow("A", REQUIRED_INTAKE["A"],
                           contributions=full_contributions(("AFS", "RESEARCH")))
        self.assertNotEqual(res.decision.status.value, "VERIFIED")

    def test_historical_evidence_never_verified(self):
        engine = make_engine()
        ev = build_evidence(engine, "HIST:1", "2020:1")
        self.assertEqual(ev.status.value, "HISTORICAL")
        contribs = [
            contrib("AFS", applicable_requirements=[CLAIM], evidence_refs=[ev.evidence_id]),
            contrib("RESEARCH", evidence_refs=[ev.evidence_id]),
        ]
        res = run_workflow("A", REQUIRED_INTAKE["A"], contributions=contribs,
                           council_engine=engine, evidences={ev.evidence_id: ev})
        self.assertNotEqual(res.decision.status.value, "VERIFIED")

    def test_claim_without_evidence_raises(self):
        # AD-1: regulatoriskt pastaende kraver evidence_refs; pipelinen vaktar.
        from kma.council.errors import PipelineError

        engine = make_engine()
        contribs = [
            contrib("AFS", applicable_requirements=[CLAIM],
                    evidence_refs=["EV-saknas-okand"]),
            contrib("RESEARCH"),
        ]
        with self.assertRaises(PipelineError):
            run_workflow("A", REQUIRED_INTAKE["A"], contributions=contribs,
                         council_engine=engine, evidences={})


class TestConflictsAndDissentPreserved(unittest.TestCase):
    def test_conflicting_evidence_gives_conflicting_status(self):
        engine = make_engine()
        ev_cur = build_evidence(engine, "AFS2023:1", "2024:1")
        ev_hist = build_evidence(engine, "HIST:1", "2020:1")
        contribs = [
            contrib("AFS", applicable_requirements=[CLAIM],
                    evidence_refs=[ev_cur.evidence_id, ev_hist.evidence_id]),
            contrib("RESEARCH",
                    evidence_refs=[ev_cur.evidence_id, ev_hist.evidence_id]),
        ]
        res = run_workflow("A", REQUIRED_INTAKE["A"], contributions=contribs,
                           council_engine=engine,
                           evidences={ev_cur.evidence_id: ev_cur,
                                      ev_hist.evidence_id: ev_hist})
        self.assertEqual(res.decision.status.value, "CONFLICTING_EVIDENCE")
        self.assertTrue(res.decision.conflicts)
        for conflict in res.decision.conflicts:
            self.assertFalse(conflict.resolved)

    def test_dissent_preserved(self):
        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:1")
        contribs = [
            contrib("AFS", evidence_refs=[ev.evidence_id],
                    dissent="AFS reserverar sig mot tolkningens omfattning."),
            contrib("RESEARCH", evidence_refs=[ev.evidence_id]),
        ]
        res = run_workflow("A", REQUIRED_INTAKE["A"], contributions=contribs,
                           council_engine=engine, evidences={ev.evidence_id: ev})
        self.assertIn("reserverar sig", res.decision.dissent)


class TestRedTeamAndRevisionGate(unittest.TestCase):
    def test_revision_routed_workflow_requires_revision_contribution(self):
        # Workflow D/E/F routar REVISION; pipelinen vaktar att bidrag finns.
        from kma.council.errors import PipelineError

        engine = make_engine()
        with self.assertRaises(PipelineError):
            run_workflow("E", REQUIRED_INTAKE["E"],
                         contributions=[contrib("AFS"), contrib("RESEARCH")],
                         council_engine=engine)

    def test_full_run_records_eleven_steps_in_audit(self):
        res = run_workflow("A", REQUIRED_INTAKE["A"],
                           contributions=full_contributions(("AFS", "RESEARCH")))
        from kma.council import PIPELINE_STEPS

        steps = [e.step for e in res.audit.events]
        core = [s for s in steps if s in PIPELINE_STEPS]
        self.assertEqual(core, list(PIPELINE_STEPS))


if __name__ == "__main__":
    unittest.main()

