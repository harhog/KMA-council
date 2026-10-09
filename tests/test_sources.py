"""KMA-002 Source Registry — end-to-end integration scenarios."""
import unittest
from datetime import date

from kma.sources import (
    AuthorityLevel,
    Currentness,
    Source,
    SourceType,
    SourceVersion,
    SourceRegistry,
    compute_checksum,
)


class TestKMA002Integration(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Valid source
    # ------------------------------------------------------------------
    def test_valid_source(self):
        s = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="Avtalsförordningen 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.avortex.nu/afs/2023:1",
            jurisdiction="SE",
            authority_level=AuthorityLevel.PRIMAR_LAG,
            effective_from=date(2023, 1, 1),
            effective_to=date(2025, 12, 31),
            retrieved_at="2025-08-01T00:00:00+02:00",
        )
        self.assertEqual(s.source_id, "AFS2023:1")
        self.assertFalse(s.is_current)

    # ------------------------------------------------------------------
    # 2. Valid source version
    # ------------------------------------------------------------------
    def test_valid_source_version(self):
        v = SourceVersion(source_id="AFS2023:1", version="2023:1",
                          effective_from=date(2023, 1, 1),
                          effective_to=date(2025, 12, 31),
                          amendment_history=["2024:01"])
        self.assertEqual(v.source_id, "AFS2023:1")
        self.assertEqual(v.version, "2023:1")
        self.assertEqual(v.amendment_history, ["2024:01"])

    # ------------------------------------------------------------------
    # 3. Current source
    # ------------------------------------------------------------------
    def test_current_source(self):
        s = Source(source_id="AFS2023:1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   version_status=Currentness.CURRENT)
        self.assertTrue(s.is_current)

    # ------------------------------------------------------------------
    # 4. Historical source
    # ------------------------------------------------------------------
    def test_historical_source(self):
        s = Source(source_id="AFS2023:2", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   version_status=Currentness.HISTORICAL)
        self.assertTrue(s.is_historical)

    # ------------------------------------------------------------------
    # 5. Unknown currentness
    # ------------------------------------------------------------------
    def test_unknown_currentness(self):
        s = Source(source_id="BLOG2025:1", publisher="X", title="Y",
                   source_type=SourceType.ANNAN, canonical_url="https://blogg.exempel.se",
                   version_status=Currentness.UNKNOWN)

    # ------------------------------------------------------------------
    # 6. Duplicate source IDs
    # ------------------------------------------------------------------
    def test_duplicate_source_ids_rejected(self):
        from kma.sources.registry import DuplicateSourceError

        r = SourceRegistry()
        s = Source(source_id="AFS2023:1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com")
        r.register(s)
        with self.assertRaises(DuplicateSourceError):
            r.register(s)

    # ------------------------------------------------------------------
    # 7. Invalid authority level
    # ------------------------------------------------------------------
    def test_invalid_authority_level(self):
        with self.assertRaises(ValueError):
            Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   authority_level="level_99")

    # ------------------------------------------------------------------
    # 8. Missing required fields
    # ------------------------------------------------------------------
    def test_missing_required_fields(self):
        with self.assertRaises(ValueError):
            Source(source_id="1", publisher="X", source_type=SourceType.AFS,
                   canonical_url="https://example.com")

    # ------------------------------------------------------------------
    # 9. Invalid effective dates
    # ------------------------------------------------------------------
    def test_invalid_effective_dates(self):
        s = Source(source_id="BLOG2025:1", publisher="X", title="Y",
                   source_type=SourceType.ANNAN, canonical_url="https://blogg.exempel.se",
                   version_status=Currentness.UNKNOWN)
        self.assertTrue(s.is_unknown)
        self.assertFalse(s.is_current)
        self.assertFalse(s.is_historical)

        with self.assertRaises(ValueError):
            Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   effective_from=date(2024, 1, 1), effective_to=date(2023, 12, 31))

    # ------------------------------------------------------------------
    # 10. Version comparison (supersedes/superseded_by)
    # ------------------------------------------------------------------
    def test_version_comparison(self):
        v2 = SourceVersion(source_id="AFS2023:2", version="2023:2",
                           supersedes="AFS2023:1")
        v3 = SourceVersion(source_id="AFS2023:3", version="2023:3",
                           superseded_by="AFS2023:2")
        self.assertEqual(v2.supersedes, "AFS2023:1")
        self.assertEqual(v3.superseded_by, "AFS2023:2")



    # ------------------------------------------------------------------
    # 11. Amendment relationship
    # ------------------------------------------------------------------
    def test_amendment_relationship(self):
        s = Source(source_id="AFS2023:2", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   amended_from_source_id="AFS2023:1")
        self.assertEqual(s.amended_from_source_id, "AFS2023:1")

    # ------------------------------------------------------------------
    # 12. Consolidated / current version
    # ------------------------------------------------------------------
    def test_consolidated_current_version(self):
        v = SourceVersion(source_id="AFS2023:1", version="2023:1",
                          consolidated=True, supersedes="AFS2023:0")
        self.assertTrue(v.is_consolidated())
        self.assertEqual(v.supersedes, "AFS2023:0")


    # ------------------------------------------------------------------
    # 13. Canonical URL validation
    # ------------------------------------------------------------------
    def test_canonical_url_validation(self):
        with self.assertRaises(ValueError):
            Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="ftp://example.com")
        with self.assertRaises(ValueError):
            Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="invalid")

    # ------------------------------------------------------------------
    # 14. Deterministic serialization / identity
    # ------------------------------------------------------------------
    def test_deterministic_serialization(self):
        s1 = Source(source_id="AFS2023:1", publisher="Arbetsmiljöverket",
                    title="AFS 2023:1", source_type=SourceType.AFS,
                    canonical_url="https://www.example.com/afs/2023:1")
        s2 = Source(source_id="AFS2023:1", publisher="Arbetsmiljöverket",
                    title="AFS 2023:1", source_type=SourceType.AFS,
                    canonical_url="https://www.example.com/afs/2023:1")
        self.assertEqual(s1, s2)
        self.assertEqual(s1.to_dict(), s2.to_dict())
        s = Source(source_id="AFS2023:1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com")
        c = compute_checksum(s)
        self.assertEqual(len(c), 64)  # SHA-256 hex
        self.assertIsNotNone(c)
        # checksum is stored as a property, no need to set
        self.assertEqual(compute_checksum(s), c)


