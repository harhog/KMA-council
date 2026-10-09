"""KMA-002 Source Registry — registry behavior tests."""
import unittest
from datetime import date

from kma.sources import (
    AuthorityLevel,
    Currentness,
    Source,
    SourceType,
    SourceRegistry,
    ValidationError,
)


class TestSourceRegistry(unittest.TestCase):
    def _make(self):
        r = SourceRegistry()
        r.register(Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
            jurisdiction="SE",
            authority_level=AuthorityLevel.PRIMAR_LAG,
            effective_from=date(2023, 1, 1),
            effective_to=date(2025, 12, 31),
            retrieved_at="2025-01-01T00:00:00+01:00",
            version_status=Currentness.CURRENT,
            checksum="abc123",
        ))
        r.register(Source(
            source_id="AFS2023:2",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:2",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:2",
            authority_level=AuthorityLevel.SEKUNDAR_SPECIALIST,
            effective_from=date(2023, 1, 1),
            effective_to=date(2024, 12, 31),
            retrieved_at="2024-01-01T00:00:00+01:00",
            version_status=Currentness.HISTORICAL,
        ))
        r.register(Source(
            source_id="BLOG2025:1",
            publisher="Blogger",
            title="Super blogg",
            source_type=SourceType.ANNAN,
            canonical_url="https://blogg.exempel.se",
            authority_level=AuthorityLevel.SEKUNDAR_SPECIALIST,
            version_status=Currentness.UNKNOWN,
        ))
        return r

    def test_register_and_get(self):
        r = self._make()
        self.assertIsNotNone(r.get("AFS2023:1"))
        self.assertIsNone(r.get("AFS2023:9"))

    def test_duplicate_rejected(self):
        r = self._make()
        s = r.get("AFS2023:1")
        with self.assertRaises(ValueError):
            r.register(s)

    def test_has(self):
        r = self._make()
        self.assertTrue(r.has("AFS2023:1"))
        self.assertFalse(r.has("missing"))

    def test_count(self):
        r = self._make()
        self.assertEqual(r.count(), 3)

    def test_current(self):
        r = self._make()
        cur = r.current()
        self.assertEqual(len(cur), 1)
        self.assertEqual(cur[0].source_id, "AFS2023:1")

    def test_historical(self):
        r = self._make()
        hist = r.historical()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0].source_id, "AFS2023:2")

    def test_unknown(self):
        r = self._make()
        unk = r.unknown()
        self.assertEqual(len(unk), 1)
        self.assertEqual(unk[0].source_id, "BLOG2025:1")

    def test_all_includes_historical_with_flag(self):
        r = self._make()
        all_now = r.all()
        self.assertEqual(len(all_now), 1)
        all_all = r.all(include_historical=True)
        self.assertEqual(len(all_all), 3)

    def test_checksum_of(self):
        r = self._make()
        self.assertEqual(r.checksum_of("AFS2023:1"), "abc123")
        self.assertIsNone(r.checksum_of("missing"))

    def test_dict_serialization(self):
        r = self._make()
        d = r.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("AFS2023:1", d)
        self.assertEqual(d["AFS2023:1"]["source_id"], "AFS2023:1")
        self.assertEqual(d["AFS2023:2"]["version_status"], "historical")

    def test_eq(self):
        r1 = self._make()
        r2 = self._make()
        self.assertEqual(r1, r2)

    def test_repr(self):
        r = SourceRegistry()
        self.assertIn("SourceRegistry", repr(r))

    def test_iter(self):
        r = self._make()
        ids = {s.source_id for s in r}
        self.assertEqual(ids, {"AFS2023:1", "AFS2023:2", "BLOG2025:1"})

    def test_clear(self):
        r = self._make()
        r.clear()
        self.assertEqual(r.count(), 0)
        self.assertIsNone(r.get("AFS2023:1"))

    def test_contains(self):
        r = self._make()
        self.assertIn("AFS2023:1", r)
        self.assertNotIn("missing", r)


class TestValidationGate(unittest.TestCase):
    def test_validation_error_is_runtime_error(self):
        e = ValidationError("missing source_id")
        self.assertIsInstance(e, ValueError)
        self.assertEqual(str(e), "missing source_id")

    def test_source_validation_error_inheritance(self):
        from kma.sources.validation import SourceValidationError

        e = SourceValidationError("bad id")
        self.assertIsInstance(e, ValueError)
