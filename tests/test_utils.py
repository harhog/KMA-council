"""KMA-002 Source Registry — deterministic serialization/checksum tests."""
import unittest

from kma.sources import Source, SourceType, SourceVersion
from kma.sources.utils import compute_checksum, deterministic_keys, normalize_for_hash


class TestDeterministicSerialization(unittest.TestCase):
    def test_dict_keys_sorted(self):
        d = {"b": 1, "a": 2}
        self.assertEqual(deterministic_keys(d), {"a": 2, "b": 1})

    def test_source_to_dict_stable(self):
        s1 = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        s2 = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        self.assertEqual(s1.to_dict(), s2.to_dict())

    def test_order_does_not_matter(self):
        s1 = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        s2 = Source(
            title="AFS 2023:1",
            canonical_url="https://www.example.com/afs/2023:1",
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            source_type=SourceType.AFS,
        )
        self.assertEqual(s1.to_dict(), s2.to_dict())

    def test_checksum_stable(self):
        s = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        c1 = compute_checksum(s)
        c2 = compute_checksum(s)
        self.assertEqual(c1, c2)

    def test_checksum_different_content(self):
        s1 = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        s2 = Source(
            source_id="AFS2023:2",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:2",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:2",
        )
        self.assertNotEqual(compute_checksum(s1), compute_checksum(s2))

    def test_checksum_same_content_different_order(self):
        s1 = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        s2 = Source(
            title="AFS 2023:1",
            canonical_url="https://www.example.com/afs/2023:1",
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            source_type=SourceType.AFS,
        )
        self.assertEqual(compute_checksum(s1), compute_checksum(s2))


class TestNormalizeForHash(unittest.TestCase):
    def test_dict_sorted(self):
        d = {"b": 1, "a": 2}
        n = normalize_for_hash(d)
        self.assertIn('"a":2', n)
        self.assertIn('"b":1', n)

    def test_source_normalized(self):
        s = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        n = normalize_for_hash(s)
        self.assertIn("AFS2023:1", n)
        self.assertIn("AFS 2023:1", n)

    def test_version_normalized(self):
        v = SourceVersion(source_id="AFS2023:1", version="2023:1",
                          supersedes="0")
        n = normalize_for_hash(v)
        self.assertIn("AFS2023:1", n)
        self.assertIn("2023:1", n)


class TestComputeChecksum(unittest.TestCase):
    def test_sha256_text(self):
        c = compute_checksum("hello world")
        self.assertEqual(len(c), 64)  # SHA-256 hex

    def test_sha256_sources(self):
        s = Source(
            source_id="AFS2023:1",
            publisher="Arbetsmiljöverket",
            title="AFS 2023:1",
            source_type=SourceType.AFS,
            canonical_url="https://www.example.com/afs/2023:1",
        )
        c = compute_checksum(s)
        self.assertEqual(len(c), 64)


if __name__ == "__main__":
    unittest.main()
