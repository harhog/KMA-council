"""KMA-005 Council Orchestration - tester del 1: fixturer + routing + intake."""
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from kma.council import (
    AgentContribution,
    Question,
    QuestionKind,
    check_intake,
    intake_question,
    load_all_contracts,
    load_contract,
    route,
)
from kma.council.errors import ContractLoadError, IntakeError, RoutingError

AS_OF = date(2026, 10, 8)
RETRIEVED_AT = datetime(2026, 9, 1, 12, 0, 0)
CLAIM = "Skyddsâtgarder kravs vid fallrisk"
QUOTE = "Arbetsgivaren ska vidta de âtgarder som behovs."
CTX = {"situation": "arbete pa hojd med fallrisk"}


def make_engine():
    from kma.evidence import EvidenceEngine
    from kma.sources import (
        AuthorityLevel, Currentness, Source, SourceRegistry, SourceType, SourceVersion,
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
    registry.register(Source(
        source_id="SEC:1", publisher="Branschforening", title="Branschvagledning",
        source_type=SourceType.BRANSCHRAD, canonical_url="https://example.com/sec/SEC:1",
        authority_level=AuthorityLevel.SEKUNDAR_SPECIALIST,
        version_status=Currentness.CURRENT))
    engine = EvidenceEngine(registry)
    engine.register_version(SourceVersion(
        source_id="AFS2023:1", version="2024:1", effective_from=date(2025, 1, 1),
        snapshot_ref="data/snapshots/2026-01-05"))
    engine.register_version(SourceVersion(
        source_id="AFS2023:1", version="2024:2", effective_from=date(2025, 1, 1)))
    engine.register_version(SourceVersion(
        source_id="HIST:1", version="2020:1", effective_from=date(2020, 1, 1),
        effective_to=date(2022, 12, 31), snapshot_ref="data/snapshots/2022-12-31"))
    engine.register_version(SourceVersion(
        source_id="SEC:1", version="2024:1", effective_from=date(2024, 1, 1),
        snapshot_ref="data/snapshots/2026-01-05"))
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


def afs_question(**overrides):
    kwargs = dict(
        question_id="Q-AFS-1",
        text="Vilken AFS-foreskrift galler for arbete pa hojd?",
        kind=QuestionKind.AFS_FRAGA, context=dict(CTX))
    kwargs.update(overrides)
    return Question(**kwargs)


class TestRouting(unittest.TestCase):
    def test_route_table_all_kinds(self):
        expected = {
            QuestionKind.AFS_FRAGA: ("AFS", "RESEARCH"),
            QuestionKind.SAM: ("SAM", "AFS", "RESEARCH"),
            QuestionKind.OSA: ("OSA", "SAM", "RESEARCH"),
            QuestionKind.BYGG: ("BYGG", "AFS", "SAM", "RISK", "RESEARCH"),
            QuestionKind.INCIDENT: ("RISK", "SAM", "REVISION", "RESEARCH"),
        }
        for kind, members in expected.items():
            with self.subTest(kind=kind.value):
                q = Question(question_id="Q", text="x", kind=kind, context=dict(CTX))
                self.assertEqual(route(q), members)

    def test_full_review_routes_whole_council(self):
        q = Question(question_id="Q", text="x", kind=QuestionKind.FULL_REVIEW, context=dict(CTX))
        result = route(q)
        self.assertEqual(len(result), 10)
        self.assertIn("CHAIR", result)
        self.assertIn("REDTEAM", result)

    def test_unknown_question_escalates(self):
        q = Question(question_id="Q", text="x", kind=QuestionKind.UNKNOWN, context=dict(CTX))
        with self.assertRaises(RoutingError):
            route(q)

    def test_unknown_with_valid_hint_returns_hint(self):
        q = Question(question_id="Q", text="x", kind=QuestionKind.UNKNOWN,
                     context=dict(CTX), route_hint=["AFS", "RESEARCH"])
        self.assertEqual(route(q), ("AFS", "RESEARCH"))

    def test_unknown_hint_with_bad_agent_raises(self):
        q = Question(question_id="Q", text="x", kind=QuestionKind.UNKNOWN,
                     context=dict(CTX), route_hint=["AFS", "NOPE"])
        with self.assertRaises(RoutingError):
            route(q)

    def test_hint_filters_table_route(self):
        self.assertEqual(route(afs_question(route_hint=["AFS"])), ("AFS",))

    def test_hint_without_match_raises(self):
        with self.assertRaises(RoutingError):
            route(afs_question(route_hint=["BYGG"]))


class TestIntake(unittest.TestCase):
    def test_valid_intake_passes(self):
        self.assertEqual(check_intake(afs_question()), [])

    def test_missing_context_gives_insufficient(self):
        from kma.council import run_pipeline

        engine = make_engine()
        q = afs_question(context={})
        result = run_pipeline(q, [], engine, {})
        self.assertEqual(result.decision.status.value, "INSUFFICIENT_EVIDENCE")
        self.assertTrue(result.decision.missing_information)

    def test_empty_text_rejected(self):
        with self.assertRaises(IntakeError):
            intake_question("Q-X", "   ", CTX)


class TestEvidenceGates(unittest.TestCase):
    def _run(self, engine, evidences, contributions):
        from kma.council import run_pipeline

        return run_pipeline(afs_question(), contributions, engine, evidences)

    def test_verified_only_after_engine_approval(self):
        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:1")
        self.assertEqual(ev.status.value, "VERIFIED")
        result = self._run(
            engine, {ev.evidence_id: ev},
            [contrib("AFS", applicable_requirements=[CLAIM], evidence_refs=[ev.evidence_id]),
             contrib("RESEARCH", evidence_refs=[ev.evidence_id])])
        self.assertEqual(result.decision.status.value, "VERIFIED")
        self.assertEqual(result.decision.evidence_refs, [ev.evidence_id])

    def test_no_snapshot_never_verified(self):
        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:2")
        self.assertNotEqual(ev.status.value, "VERIFIED")
        result = self._run(
            engine, {ev.evidence_id: ev},
            [contrib("AFS", applicable_requirements=[CLAIM], evidence_refs=[ev.evidence_id]),
             contrib("RESEARCH", evidence_refs=[ev.evidence_id])])
        self.assertNotEqual(result.decision.status.value, "VERIFIED")

    def test_historical_never_current(self):
        engine = make_engine()
        ev = build_evidence(engine, "HIST:1", "2020:1")
        self.assertEqual(ev.status.value, "HISTORICAL")
        result = self._run(
            engine, {ev.evidence_id: ev},
            [contrib("AFS", applicable_requirements=[CLAIM], evidence_refs=[ev.evidence_id]),
             contrib("RESEARCH", evidence_refs=[ev.evidence_id])])
        self.assertIn(result.decision.status.value, ("HISTORICAL", "CONFLICTING_EVIDENCE"))
        self.assertNotEqual(result.decision.status.value, "VERIFIED")

    def test_secondary_alone_never_verified(self):
        engine = make_engine()
        ev = build_evidence(engine, "SEC:1", "2024:1")
        self.assertEqual(ev.status.value, "UNVERIFIED")
        result = self._run(
            engine, {ev.evidence_id: ev},
            [contrib("AFS", applicable_requirements=[CLAIM], evidence_refs=[ev.evidence_id]),
             contrib("RESEARCH", evidence_refs=[ev.evidence_id])])
        self.assertNotEqual(result.decision.status.value, "VERIFIED")

    def test_claim_without_evidence_raises(self):
        from kma.council.errors import PipelineError

        engine = make_engine()
        with self.assertRaises(PipelineError):
            from kma.council import run_pipeline

            run_pipeline(
                afs_question(),
                [contrib("AFS", assessment="Krav galler.",
                         applicable_requirements=[CLAIM],
                         evidence_refs=["EV-saknas-okand"]),
                 contrib("RESEARCH")],
                engine, {})

    def test_unknown_evidence_ref_raises(self):
        from kma.council import run_pipeline
        from kma.council.errors import PipelineError

        engine = make_engine()
        with self.assertRaises(PipelineError):
            run_pipeline(
                afs_question(),
                [contrib("AFS", evidence_refs=["EV-finns-ej"]),
                 contrib("RESEARCH")],
                engine, {})

    def test_gate_statuses_distinct_from_evidence(self):
        from kma.council import DecisionStatus
        from kma.evidence import EvidenceStatus

        evidence_values = {s.value for s in EvidenceStatus}
        self.assertNotIn("INSUFFICIENT_EVIDENCE", evidence_values)
        self.assertNotIn("CONFLICTING_EVIDENCE", evidence_values)
        self.assertIn("INSUFFICIENT_EVIDENCE", {s.value for s in DecisionStatus})


class TestConflictsAndDissent(unittest.TestCase):
    def test_conflicting_sources_give_conflicting_evidence(self):
        from kma.council import run_pipeline

        engine = make_engine()
        ev_new = build_evidence(engine, "AFS2023:1", "2024:1")
        ev_old = build_evidence(engine, "HIST:1", "2020:1")
        self.assertNotEqual(ev_new.status, ev_old.status)
        result = run_pipeline(
            afs_question(),
            [contrib("AFS", applicable_requirements=[CLAIM],
                     evidence_refs=[ev_new.evidence_id, ev_old.evidence_id]),
             contrib("RESEARCH", evidence_refs=[ev_new.evidence_id, ev_old.evidence_id])],
            engine, {ev_new.evidence_id: ev_new, ev_old.evidence_id: ev_old})
        self.assertEqual(result.decision.status.value, "CONFLICTING_EVIDENCE")
        self.assertTrue(result.decision.conflicts)
        for conflict in result.decision.conflicts:
            self.assertFalse(conflict.resolved)

    def test_dissent_preserved_in_decision(self):
        from kma.council import run_pipeline

        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:1")
        result = run_pipeline(
            afs_question(),
            [contrib("AFS", evidence_refs=[ev.evidence_id],
                     dissent="AFS reserverar sig mot tolkningens omfattning."),
             contrib("RESEARCH", evidence_refs=[ev.evidence_id])],
            engine, {ev.evidence_id: ev})
        self.assertIn("AFS", result.decision.dissent)
        self.assertIn("reserverar sig", result.decision.dissent)


class TestRedTeamReview(unittest.TestCase):
    def test_findings_before_synthesis(self):
        from kma.council import run_pipeline
        from kma.council.models import QuestionKind

        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:1")
        q = Question(question_id="Q-FULL", text="Full review av fallskydd.",
                     kind=QuestionKind.FULL_REVIEW, context=dict(CTX))
        contributions = [
            contrib("CHAIR", assessment="Sammanvagning."),
            contrib("AFS", applicable_requirements=[CLAIM],
                    evidence_refs=[ev.evidence_id]),
            contrib("SAM"), contrib("OSA"), contrib("BYGG"),
            contrib("RISK", risks=["Fallrisk vid halt underlag."]),
            contrib("PRAKTIK"),
            contrib("REVISION", missing_information=["Protokoll saknas."]),
            contrib("REDTEAM", risks=["Motbevis: undantag for kortvarigt arbete."]),
            contrib("RESEARCH", evidence_refs=[ev.evidence_id]),
        ]
        result = run_pipeline(q, contributions, engine, {ev.evidence_id: ev})
        self.assertTrue(result.decision.red_team_findings)
        self.assertTrue(result.decision.revision_findings)
        steps = [e.step for e in result.audit.events]
        self.assertLess(steps.index("red_team_review"), steps.index("chair_synthesis"))
        self.assertLess(steps.index("chair_synthesis"), steps.index("final_output"))

    def test_routed_redteam_missing_raises(self):
        from kma.council import run_pipeline
        from kma.council.errors import PipelineError
        from kma.council.models import QuestionKind

        engine = make_engine()
        q = Question(question_id="Q-FULL", text="Full review av fallskydd.",
                     kind=QuestionKind.FULL_REVIEW, context=dict(CTX))
        with self.assertRaises(PipelineError):
            run_pipeline(q, [contrib("AFS"), contrib("SAM"),
                             contrib("RESEARCH")],
                         engine, {})


class TestDeterminismAndSteps(unittest.TestCase):
    def _full_run(self):
        from kma.council import run_pipeline

        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:1")
        contributions = [
            contrib("AFS", applicable_requirements=[CLAIM],
                    evidence_refs=[ev.evidence_id]),
            contrib("RESEARCH", evidence_refs=[ev.evidence_id]),
        ]
        return run_pipeline(afs_question(), contributions, engine,
                            {ev.evidence_id: ev})

    def test_eleven_steps_audited_in_order(self):
        from kma.council import PIPELINE_STEPS

        result = self._full_run()
        steps = [e.step for e in result.audit.events]
        core = [s for s in steps if s in PIPELINE_STEPS]
        self.assertEqual(core, list(PIPELINE_STEPS))
        seqs = [e.seq for e in result.audit.events]
        self.assertEqual(seqs, list(range(len(seqs))))

    def test_same_input_same_output(self):
        first = self._full_run()
        second = self._full_run()
        self.assertEqual(first.decision.decision_id, second.decision.decision_id)
        self.assertEqual(first.decision.model_dump(), second.decision.model_dump())

    def test_order_does_not_matter(self):
        from kma.council import run_pipeline

        engine = make_engine()
        ev = build_evidence(engine, "AFS2023:1", "2024:1")
        contributions = [
            contrib("RESEARCH", evidence_refs=[ev.evidence_id]),
            contrib("AFS", applicable_requirements=[CLAIM],
                    evidence_refs=[ev.evidence_id]),
        ]
        result = run_pipeline(afs_question(), contributions, engine,
                              {ev.evidence_id: ev})
        self.assertEqual(result.decision.status.value, "VERIFIED")

    def test_missing_routed_contribution_raises(self):
        from kma.council import run_pipeline
        from kma.council.errors import PipelineError

        engine = make_engine()
        with self.assertRaises(PipelineError):
            run_pipeline(afs_question(), [contrib("AFS")], engine, {})

    def test_no_llm_no_network(self):
        import inspect

        import kma.council.pipeline as pipeline_mod

        source = inspect.getsource(pipeline_mod).lower()
        for forbidden in ("urllib", "requests", "httpx", "socket",
                          "openai", "anthropic", "transformers"):
            self.assertNotIn(forbidden, source)
