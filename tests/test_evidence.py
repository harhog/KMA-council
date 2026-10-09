"""KMA-003 Evidence Engine — betendes- och säkerhetstester.

Testar säkerhetsinvarianter (regel 1-10 i KMA-003), inte bara konstruktion.
"""
import unittest
from datetime import date, datetime

from kma.evidence import (
    Evidence,
    EvidenceEngine,
    EvidenceStatus,
    EvidenceValidationError,
    UnknownSourceError,
    UnknownSourceVersionError,
)
from kma.sources import (
    AuthorityLevel,
    Currentness,
    Source,
    SourceRegistry,
    SourceType,
    SourceVersion,
)

AS_OF = date(2026, 10, 8)
RETRIEVED_AT = datetime(2026, 9, 1, 12, 0, 0)
CLAIM = "Skyddskrävande åtgärder krävs när fallrisk finns"
QUOTE = "Arbetsgivaren ska vidta de åtgärder som behövs."


def make_engine(
    *,
    authority=AuthorityLevel.PRIMAR_LAG,
    version_status=Currentness.CURRENT,
    source_id="AFS2023:1",
    source_type=SourceType.AFS,
):
    """Bygg ett register med en källa och tre källversioner."""
    registry = SourceRegistry()
    registry.register(
        Source(
            source_id=source_id,
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=source_type,
            canonical_url=f"https://example.com/afs/{source_id}",
            authority_level=authority,
            version_status=version_status,
        )
    )
    engine = EvidenceEngine(registry)
    engine.register_version(
        SourceVersion(
            source_id=source_id,
            version="2023:1",
            effective_from=date(2023, 1, 1),
            effective_to=date(2024, 12, 31),
            superseded_by=f"{source_id}/2024:1",
            snapshot_ref="data/snapshots/2024-12-31",
        )
    )
    engine.register_version(
        SourceVersion(
            source_id=source_id,
            version="2024:1",
            effective_from=date(2025, 1, 1),
            snapshot_ref="data/snapshots/2026-01-05",
        )
    )
    engine.register_version(
        SourceVersion(
            source_id=source_id,
            version="2027:1",
            effective_from=date(2027, 1, 1),
            snapshot_ref="data/snapshots/2026-01-05",
        )
    )
    return engine


def valid_kwargs(**overrides):
    """Standardargument som uppfyller alla verifieringskrav (§6)."""
    kwargs = dict(
        source_id="AFS2023:1",
        version="2024:1",
        locator="AFS 2023:1 kapitel 5 paragraf 3 stycket 2",
        claim_supported=CLAIM,
        as_of=AS_OF,
        effective_date=date(2026, 6, 1),
        retrieved_at=RETRIEVED_AT,
        quote_or_excerpt=QUOTE,
    )
    kwargs.update(overrides)
    return kwargs


class TestKMA003Integration(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Giltig evidens med känd källa och version
    # ------------------------------------------------------------------
    def test_valid_evidence_known_source_and_version(self):
        engine = make_engine()
        e = engine.build(**valid_kwargs())
        self.assertEqual(e.status, EvidenceStatus.VERIFIED)
        self.assertTrue(e.is_verified)
        self.assertEqual(e.source_type, SourceType.AFS)
        self.assertEqual(e.authority_level, AuthorityLevel.PRIMAR_LAG)
        self.assertEqual(e.source_version, "AFS2023:1/2024:1")

    # ------------------------------------------------------------------
    # 2. Okänd källa
    # ------------------------------------------------------------------
    def test_unknown_source(self):
        engine = make_engine()
        with self.assertRaises(UnknownSourceError):
            engine.build(**valid_kwargs(source_id="SAKNAS:1"))

    # ------------------------------------------------------------------
    # 3. Okänd källversion
    # ------------------------------------------------------------------
    def test_unknown_source_version(self):
        engine = make_engine()
        with self.assertRaises(UnknownSourceVersionError):
            engine.build(**valid_kwargs(version="2099:9"))

    # ------------------------------------------------------------------
    # 4. Saknad eller ogiltig locator
    # ------------------------------------------------------------------
    def test_missing_or_invalid_locator(self):
        engine = make_engine()
        with self.assertRaises(ValueError):
            engine.build(**valid_kwargs(locator=""))
        with self.assertRaises(ValueError):
            engine.build(**valid_kwargs(locator="paragraf utan siffra"))

    # ------------------------------------------------------------------
    # 5. Saknat påstående
    # ------------------------------------------------------------------
    def test_missing_claim(self):
        engine = make_engine()
        with self.assertRaises(ValueError):
            engine.build(**valid_kwargs(claim_supported=""))
        with self.assertRaises(ValueError):
            engine.build(**valid_kwargs(claim_supported="   "))

    # ------------------------------------------------------------------
    # 6. Historisk evidens får aldrig presenteras som aktuell rätt
    # ------------------------------------------------------------------
    def test_historical_evidence(self):
        engine = make_engine()
        old = engine.build(**valid_kwargs(version="2023:1"))
        self.assertEqual(old.status, EvidenceStatus.HISTORICAL)
        self.assertTrue(old.is_historical)
        self.assertNotEqual(old.status, EvidenceStatus.VERIFIED)
        self.assertEqual(old.to_dict()["status"], "HISTORICAL")
        self.assertEqual(engine.verify_claim([old]), EvidenceStatus.HISTORICAL)

    def test_historical_source_current_version(self):
        engine = make_engine(version_status=Currentness.HISTORICAL)
        e = engine.build(**valid_kwargs())
        self.assertEqual(e.status, EvidenceStatus.HISTORICAL)
        self.assertNotEqual(e.status, EvidenceStatus.VERIFIED)

    # ------------------------------------------------------------------
    # 7. Framtida ikraftträdande
    # ------------------------------------------------------------------
    def test_future_effective_date(self):
        engine = make_engine()
        future = engine.build(**valid_kwargs(version="2027:1"))
        self.assertEqual(future.status, EvidenceStatus.UNVERIFIED)
        self.assertNotEqual(future.status, EvidenceStatus.VERIFIED)
        self.assertNotEqual(future.status, EvidenceStatus.HISTORICAL)

    # ------------------------------------------------------------------
    # 8. Otillåten automatisk VERIFIED
    # ------------------------------------------------------------------
    def test_status_cannot_be_set_via_input(self):
        engine = make_engine()
        # build() har inget status-parameter: indata kan inte sätta VERIFIED.
        with self.assertRaises(TypeError):
            engine.build(**valid_kwargs(status=EvidenceStatus.VERIFIED))

    def test_verified_requires_all_requirements(self):
        engine = make_engine()
        # Utan referenser avvisas VERIFIED direkt (regel 1 och 8).
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id="EV-x",
                source_id="AFS2023:1",
                source_version="AFS2023:1/2024:1",
                locator="AFS 2023:1 kapitel 5 paragraf 3",
                claim_supported=CLAIM,
                status=EvidenceStatus.VERIFIED,
            )
        # Med referenser men utan textstöd avvisas VERIFIED (regel 4).
        good = engine.build(**valid_kwargs())
        source, version = engine.trace(good)
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id=good.evidence_id,
                source_id=good.source_id,
                source_version=good.source_version,
                locator=good.locator,
                claim_supported=good.claim_supported,
                effective_date=good.effective_date,
                retrieved_at=good.retrieved_at,
                status=EvidenceStatus.VERIFIED,
                source_ref=source,
                version_ref=version,
            )
        # Ej hämtad text ger aldrig VERIFIED (regel 9).
        unfetched = engine.build(**valid_kwargs(retrieved_at=None))
        self.assertEqual(unfetched.status, EvidenceStatus.UNVERIFIED)

    # ------------------------------------------------------------------
    # 9. Deterministiskt ID och checksumma/serialisering
    # ------------------------------------------------------------------
    def test_deterministic_id_and_checksum(self):
        engine = make_engine()
        a = engine.build(**valid_kwargs())
        b = engine.build(**valid_kwargs())
        self.assertEqual(a.evidence_id, b.evidence_id)
        self.assertEqual(a.checksum(), b.checksum())
        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertTrue(a.evidence_id.startswith("EV-"))
        self.assertEqual(len(a.checksum()), 64)
        c = engine.build(**valid_kwargs(locator="AFS 2023:1 kapitel 5 paragraf 4"))
        self.assertNotEqual(a.evidence_id, c.evidence_id)

    # ------------------------------------------------------------------
    # 10. Ändrad källversion
    # ------------------------------------------------------------------
    def test_changed_source_version(self):
        engine = make_engine()
        old = engine.build(**valid_kwargs(version="2023:1"))
        new = engine.build(**valid_kwargs(version="2024:1"))
        self.assertEqual(old.status, EvidenceStatus.HISTORICAL)
        self.assertEqual(new.status, EvidenceStatus.VERIFIED)
        self.assertNotEqual(old.evidence_id, new.evidence_id)
        _, old_version = engine.trace(old)
        _, new_version = engine.trace(new)
        self.assertEqual(old_version.version, "2023:1")
        self.assertEqual(new_version.version, "2024:1")

    # ------------------------------------------------------------------
    # 11. Motstridiga evidensobjekt representeras utan tyst lösning
    # ------------------------------------------------------------------
    def test_conflicting_evidence(self):
        engine = make_engine()
        old = engine.build(**valid_kwargs(version="2023:1"))
        new = engine.build(**valid_kwargs(version="2024:1"))
        conflicts = engine.detect_conflicts([old, new])
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict.claim_supported, CLAIM)
        self.assertIn(EvidenceStatus.HISTORICAL, conflict.statuses)
        self.assertIn(EvidenceStatus.VERIFIED, conflict.statuses)
        self.assertFalse(conflict.resolved)
        # Upptäckten ändrar inga objekt (konflikten tystlys aldrig).
        self.assertEqual(old.status, EvidenceStatus.HISTORICAL)
        self.assertEqual(new.status, EvidenceStatus.VERIFIED)
        # Explicit konfliktmarkering kräver beskrivning.
        with self.assertRaises(EvidenceValidationError):
            engine.mark_conflicting(new, "   ")
        marked = engine.mark_conflicting(new, "2023:1 och 2024:1 ger olika innebörd")
        self.assertEqual(marked.status, EvidenceStatus.CONFLICTING)
        self.assertEqual(marked.limitations, "2023:1 och 2024:1 ger olika innebörd")
        # Modellen avvisar CONFLICTING utan limitations.
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id=new.evidence_id,
                source_id=new.source_id,
                source_version=new.source_version,
                locator=new.locator,
                claim_supported=new.claim_supported,
                status=EvidenceStatus.CONFLICTING,
                source_ref=new.source_ref,
                version_ref=new.version_ref,
            )

    # ------------------------------------------------------------------
    # 12. Partiell eller otillräcklig evidens
    # ------------------------------------------------------------------
    def test_partial_or_insufficient_evidence(self):
        # Nivå-3-källa med fullständig metadata → PARTIALLY, aldrig VERIFIED.
        engine3 = make_engine(
            authority=AuthorityLevel.ALLMANNAT_RAD, source_id="RAD2025:1"
        )
        partial = engine3.build(**valid_kwargs(source_id="RAD2025:1"))
        self.assertEqual(partial.status, EvidenceStatus.PARTIALLY_VERIFIED)
        # Nivå-1, hämtad text men utan utdrag → otillräckligt, ej VERIFIED.
        engine = make_engine()
        no_excerpt = engine.build(**valid_kwargs(quote_or_excerpt=None))
        self.assertEqual(no_excerpt.status, EvidenceStatus.PARTIALLY_VERIFIED)

    # ------------------------------------------------------------------
    # 13. Okänd aktuell status
    # ------------------------------------------------------------------
    def test_unknown_current_status(self):
        engine = make_engine(version_status=Currentness.UNKNOWN)
        e = engine.build(**valid_kwargs())
        self.assertEqual(e.status, EvidenceStatus.UNVERIFIED)
        self.assertEqual(engine.verify_claim([e]), EvidenceStatus.UNVERIFIED)
        self.assertNotEqual(e.status, EvidenceStatus.VERIFIED)

    # ------------------------------------------------------------------
    # 14. Spårbarhet från evidens till exakt källversion
    # ------------------------------------------------------------------
    def test_traceability_to_exact_version(self):
        engine = make_engine()
        e = engine.build(**valid_kwargs())
        source, version = engine.trace(e)
        self.assertEqual(source.source_id, e.source_id)
        self.assertEqual(version.version, "2024:1")
        self.assertEqual(e.source_version, "AFS2023:1/2024:1")
        data = e.to_dict()
        self.assertEqual(data["source_id"], "AFS2023:1")
        self.assertEqual(data["source_version"], "AFS2023:1/2024:1")

    # ------------------------------------------------------------------
    # 15. Sekundär källa som enda stöd för regulatoriskt påstående
    # ------------------------------------------------------------------
    def test_secondary_source_as_sole_support(self):
        engine = make_engine(
            authority=AuthorityLevel.SEKUNDAR_SPECIALIST, source_id="BLOGG2025:1"
        )
        secondary = engine.build(**valid_kwargs(source_id="BLOGG2025:1"))
        self.assertEqual(secondary.status, EvidenceStatus.UNVERIFIED)
        self.assertEqual(engine.verify_claim([secondary]), EvidenceStatus.UNVERIFIED)
        self.assertNotEqual(engine.verify_claim([secondary]), EvidenceStatus.VERIFIED)

    # ------------------------------------------------------------------
    # 16. Påståendegate: aldrig bättre än svagaste evidensen
    # ------------------------------------------------------------------
    def test_claim_gate(self):
        engine = make_engine()
        # Utan evidens → aldrig VERIFIED.
        self.assertEqual(engine.verify_claim([]), EvidenceStatus.UNVERIFIED)
        good = engine.build(**valid_kwargs())
        self.assertEqual(engine.verify_claim([good]), EvidenceStatus.VERIFIED)
        old = engine.build(**valid_kwargs(version="2023:1"))
        self.assertEqual(engine.verify_claim([good, old]), EvidenceStatus.HISTORICAL)

    # ------------------------------------------------------------------
    # 17. Saknad källreferens och ogiltigt versionsformat
    # ------------------------------------------------------------------
    def test_missing_source_reference(self):
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id="EV-1",
                source_id="AFS2023:1",
                source_version="AFS2023:1/2024:1",
                locator="AFS 2023:1 kapitel 5 paragraf 3",
                claim_supported=CLAIM,
            )
        engine = make_engine()
        good = engine.build(**valid_kwargs())
        source, version = engine.trace(good)
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id=good.evidence_id,
                source_id=good.source_id,
                source_version="2024:1",
                locator=good.locator,
                claim_supported=good.claim_supported,
                source_ref=source,
                version_ref=version,
            )


if __name__ == "__main__":
    unittest.main()
