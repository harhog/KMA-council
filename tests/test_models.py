"""KMA-002 Source Registry — model behavior tests."""
import unittest
from datetime import date

from kma.sources import (
    AuthorityLevel,
    Currentness,
    Source,
    SourceType,
    SourceVersion,
)


class TestSourceBasic(unittest.TestCase):
    def setUp(self):
        self.data = {
            "source_id": "AFS2023:1",
            "publisher": "Arbetsmiljöverket",
            "title": "Avtalsförordningen (AFS 2023:1)",
            "source_type": SourceType.AFS,
            "canonical_url": "https://www.example.com/afs/2023:1",
            "jurisdiction": "SE",
            "authority_level": AuthorityLevel.PRIMAR_LAG,
        }

    def test_valid_source(self):
        s = Source(**self.data)
        self.assertEqual(s.source_id, "AFS2023:1")
        self.assertEqual(s.authority_level, AuthorityLevel.PRIMAR_LAG)
        self.assertFalse(s.is_current)

    def test_default_version_status_unknown(self):
        s = Source(**self.data)
        self.assertEqual(s.version_status, Currentness.UNKNOWN)

    def test_to_dict(self):
        s = Source(**self.data)
        d = s.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["source_id"], "AFS2023:1")
        self.assertEqual(d["authority_level"], "level_1")

    def test_eq_identity(self):
        s1 = Source(**self.data)
        s2 = Source(**self.data)
        self.assertEqual(s1, s2)

    def test_not_eq_different_id(self):
        data_without_id = {k: v for k, v in self.data.items() if k != "source_id"}
        s1 = Source(**self.data)
        s2 = Source(**data_without_id, source_id="AFS2023:2")
        self.assertNotEqual(s1, s2)

    def test_deterministic_serialization(self):
        s1 = Source(**self.data)
        s2 = Source(**self.data)
        self.assertEqual(s1.to_dict(), s2.to_dict())

    def test_from_dict_roundtrip(self):
        s1 = Source(**self.data)
        s2 = Source.from_dict(s1.to_dict())
        self.assertEqual(s1, s2)

    def test_model_config_forbid_extra(self):
        with self.assertRaises(ValueError):
            Source(**self.data, extra_field="x")


class TestSourceValidation(unittest.TestCase):
    def _base(self):
        return {
            "source_id": "1",
            "publisher": "X",
            "title": "Y",
            "source_type": SourceType.AFS,
            "canonical_url": "https://example.com",
        }

    def test_missing_source_id(self):
        with self.assertRaises(ValueError):
            Source(**{k: v for k, v in self._base().items() if k != "source_id"})

    def test_missing_title(self):
        with self.assertRaises(ValueError):
            Source(**{k: v for k, v in self._base().items() if k != "title"})

    def test_blank_source_id(self):
        with self.assertRaises(ValueError):
            Source(**{k: v for k, v in self._base().items() if k != "source_id"}, source_id="   ")

    def test_invalid_url_scheme(self):
        with self.assertRaises(ValueError):
            Source(**{k: v for k, v in self._base().items() if k != "canonical_url"}, canonical_url="ftp://example.com")

    def test_authority_level_enum(self):
        s = Source(**self._base(), authority_level=AuthorityLevel.SEKUNDAR_SPECIALIST)
        self.assertEqual(s.authority_level, AuthorityLevel.SEKUNDAR_SPECIALIST)

    def test_invalid_authority_level(self):
        with self.assertRaises(ValueError):
            Source(**self._base(), authority_level="level_99")

class TestSourceDates(unittest.TestCase):
    def test_effective_from_gt_effective_to(self):
        with self.assertRaises(ValueError):
            Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   effective_from=date(2024, 1, 1), effective_to=date(2023, 12, 31))

    def test_effective_from_none(self):
        s = Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com")
        self.assertIsNone(s.effective_from)

    def test_effective_to_optional(self):
        s = Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   effective_to=date(2023, 12, 31))
        self.assertEqual(s.effective_to, date(2023, 12, 31))


class TestSourceNormalizedFields(unittest.TestCase):
    def test_topics_csv(self):
        s = Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   topics="AFS,Lag,Recipros")
        self.assertEqual(s.topics, ["AFS", "Lag", "Recipros"])

    def test_topics_stripped(self):
        s = Source(source_id="1", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   topics=[" AFS ", " Lag "])
        self.assertEqual(s.topics, ["AFS", "Lag"])

    def test_amended_from(self):
        s = Source(source_id="AFS2023:2", publisher="X", title="Y",
                   source_type=SourceType.AFS, canonical_url="https://example.com",
                   amended_from_source_id="AFS2023:1")
        self.assertEqual(s.amended_from_source_id, "AFS2023:1")


class TestSourceVersion(unittest.TestCase):
    def test_valid_version(self):
        v = SourceVersion(source_id="AFS2023:1", version="2023:1")
        self.assertFalse(v.is_consolidated())

    def test_consolidated(self):
        v = SourceVersion(source_id="AFS2023:1", version="2023:1",
                          consolidated=True)
        self.assertTrue(v.is_consolidated())

    def test_supersedes(self):
        v = SourceVersion(source_id="AFS2023:2", version="2023:2",
                          supersedes="AFS2023:1")
        self.assertEqual(v.supersedes, "AFS2023:1")

    def test_superseded_by(self):
        v = SourceVersion(source_id="AFS2023:1", version="2023:1",
                          superseded_by="AFS2023:2")
        self.assertEqual(v.superseded_by, "AFS2023:2")

    def test_effective_dates_validation(self):
        with self.assertRaises(ValueError):
            SourceVersion(source_id="1", version="1",
                          effective_from=date(2024, 1, 1),
                          effective_to=date(2023, 12, 31))

    def test_future_version(self):
        v = SourceVersion(source_id="1", version="future",
                          effective_to=date(2099, 12, 31))
        self.assertTrue(v.is_future_version())

    def test_not_future(self):
        v = SourceVersion(source_id="1", version="2023:1")
        self.assertFalse(v.is_future_version())

    def test_to_dict(self):
        v = SourceVersion(source_id="1", version="1",
                          consolidated=True, supersedes="0")
        d = v.to_dict()
        self.assertTrue(d["consolidated"])
        self.assertEqual(d["supersedes"], "0")

    def test_to_dict_include_none(self):
        v = SourceVersion(source_id="1", version="1")
        d = v.to_dict(include_none=True)
        self.assertIn("effective_from", d)
        self.assertIn("effective_to", d)


class TestSourceCurrentness(unittest.TestCase):
    def _base(self):
        return {
            "source_id": "1",
            "publisher": "X",
            "title": "Y",
            "source_type": SourceType.AFS,
            "canonical_url": "https://example.com",
        }

    def test_current(self):
        s = Source(**self._base(), version_status=Currentness.CURRENT)
        self.assertTrue(s.is_current)

    def test_historical(self):
        s = Source(**self._base(), version_status=Currentness.HISTORICAL)
        self.assertTrue(s.is_historical)

    def test_unknown(self):
        s = Source(**self._base(), version_status=Currentness.UNKNOWN)
        self.assertTrue(s.is_unknown)
        self.assertFalse(s.is_current)
