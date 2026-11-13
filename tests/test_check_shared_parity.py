# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for scripts/check_shared_parity.py (standard library only)."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_shared_parity as parity  # noqa: E402


def entry_for(data, local, upstream):
    return {"local": local, "upstream": upstream, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


class ProvenanceShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prov = parity.load_provenance()

    def test_pinned_source_is_the_v050_release_commit(self):
        source = self.prov["source"]
        self.assertEqual(source["commit"],
                         "170e677fbb6726a3f765373dbe1f214820000be7")
        self.assertEqual(source["tag"], "v0.5.0")
        self.assertEqual(self.prov["fhpContract"]["schemaVersion"], "1.1")

    def test_adjusted_entries_record_both_digests(self):
        for entry in self.prov["copied"]:
            if "adjustment" in entry:
                self.assertIn("upstreamSha256", entry, entry["local"])
                self.assertNotEqual(entry["sha256"], entry["upstreamSha256"])
            if entry.get("commit"):
                self.assertIn("commitNote", entry)

    def test_strict_dirs_classify_the_whole_tree(self):
        errors, listed = parity.check_local(self.prov)
        self.assertEqual(errors, [], "recorded digests drifted")
        self.assertEqual(parity.check_extras(self.prov, listed), [])

    def test_companion_entry_points_at_the_post_tag_fix(self):
        by_local = {e["local"]: e for e in self.prov["copied"]}
        rich = by_local["examples/fhp/rich-predicted.fhp.yaml"]
        self.assertEqual(rich["commit"],
                         "e1e5998709a6df922b83bb89e6a2bf5c5d27d87d")


class PinnedSectionTests(unittest.TestCase):
    """The Q2 freeze: inherited FHR/FHGFF3 artifacts are digest-pinned fixtures."""

    REQUIRED = {
        "fhr.json", "fhr_linkml.yml", "fhgff3.json", "fhgff3_linkml.yml",
        "schemas/core.yaml", "jsonld/fhr.context.jsonld", "jsonld/terms.jsonld",
        "jsonld/terms.ttl", "docs/TERMS.md", "docs/MAPPINGS.md",
        "examples/example.fhr.jsonld", "examples/minimal.fhr.jsonld",
        "examples/example.fhr.export.jsonld",
    }

    def test_the_inherited_chain_is_fully_pinned(self):
        prov = parity.load_provenance()
        pinned = {entry["local"]: entry for entry in prov["pinned"]}
        self.assertTrue(self.REQUIRED <= set(pinned),
                        self.REQUIRED - set(pinned))
        # Every schema.org export expectation (make_jsonld's generated outputs)
        # is pinned too, and every entry names its historical source commit.
        export_fixtures = {path.relative_to(parity.ROOT).as_posix()
                           for path in (parity.ROOT / "tests/fixtures/schemaorg-export").glob(
                               "*/expected.jsonld")}
        self.assertTrue(export_fixtures <= set(pinned), export_fixtures - set(pinned))
        for entry in pinned.values():
            self.assertEqual(entry["commit"],
                             "43f9067d0ce21e9ae63fd9eee64f9c2af0b73ff4", entry["local"])
            self.assertIn("upstream", entry)

    def test_pinned_files_match_their_recorded_digests(self):
        # check_local covers the pinned section, so drift fails CI offline.
        prov = parity.load_provenance()
        errors, listed = parity.check_local(prov)
        self.assertEqual(errors, [])
        for entry in prov["pinned"]:
            self.assertIn(entry["local"], listed)

    def test_pinned_drift_is_reported(self):
        data = b'{"pinned": "bytes"}\n'
        entry = entry_for(data, "fhr.json", "fhr.json")
        entry["commit"] = "43f9067d0ce21e9ae63fd9eee64f9c2af0b73ff4"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fhr.json").write_bytes(b"tampered\n")
            prov = {"copied": [], "pinned": [entry], "legacy": [], "owned": [],
                    "strictDirs": []}
            with mock.patch.object(parity, "ROOT", root):
                errors, _ = parity.check_local(prov)
        self.assertEqual(len(errors), 2)  # size and content
        self.assertTrue(all("fhr.json" in error for error in errors))


class AdjustmentTests(unittest.TestCase):
    def test_provenance_header_is_prepended(self):
        adjustment = {"kind": "provenance-header", "header": "# pin\n"}
        self.assertEqual(parity.apply_adjustment(b"payload\n", adjustment),
                         b"# pin\npayload\n")

    def test_import_retarget_replaces_exactly_one_line(self):
        adjustment = {"kind": "import-retarget", "from": "- schemas/core\n",
                      "to": "- schemas/core-v0.5\n"}
        out = parity.apply_adjustment(b"imports:\n- schemas/core\n", adjustment)
        self.assertEqual(out, b"imports:\n- schemas/core-v0.5\n")
        with self.assertRaises(ValueError):
            parity.apply_adjustment(b"imports:\n", adjustment)
        with self.assertRaises(ValueError):
            parity.apply_adjustment(b"a\n- schemas/core\nb\n- schemas/core\n",
                                    adjustment)

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            parity.apply_adjustment(b"", {"kind": "symlink"})


class CheckLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def run_check(self, files, pin_overrides=None):
        for local, data in files.items():
            path = self.root / local
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        entries = [entry_for(data, local, local) for local, data in files.items()]
        prov = {"copied": entries, "legacy": [], "owned": [], "strictDirs": []}
        for local, patch in (pin_overrides or {}).items():
            next(e for e in prov["copied"] if e["local"] == local).update(patch)
        with mock.patch.object(parity, "ROOT", self.root):
            return parity.check_local(prov)

    def test_matching_digests_pass(self):
        errors, listed = self.run_check({"schemas/versions.json": b"{}\n"})
        self.assertEqual(errors, [])
        self.assertIn("schemas/versions.json", listed)

    def test_drifted_content_and_size_are_reported(self):
        errors, _ = self.run_check(
            {"schemas/versions.json": b"{}\n"},
            {"schemas/versions.json": {"sha256": "0" * 64, "size": 99}})
        self.assertEqual(len(errors), 2)

    def test_missing_file_is_reported(self):
        errors, _ = self.run_check({})
        self.assertEqual(errors, [])
        prov = {"copied": [entry_for(b"x", "schemas/gone.yaml", "schemas/gone.yaml")],
                "legacy": [], "owned": [], "strictDirs": []}
        with mock.patch.object(parity, "ROOT", self.root):
            errors, _ = parity.check_local(prov)
        self.assertEqual(errors, ["missing: schemas/gone.yaml"])


class StrictDirTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def extras(self, prov):
        listed = {e["local"]: e for e in prov["copied"]}
        with mock.patch.object(parity, "ROOT", self.root):
            return parity.check_extras(prov, listed)

    def test_unclassified_new_path_fails(self):
        (self.root / "schemas").mkdir()
        (self.root / "schemas/core.yaml").write_text("x\n")
        (self.root / "schemas/surprise.yaml").write_text("x\n")
        prov = {"copied": [entry_for(b"x\n", "schemas/core.yaml", "schemas/core.yaml")],
                "legacy": [{"path": "schemas/other.yaml"}], "owned": [],
                "strictDirs": ["schemas"]}
        errors = self.extras(prov)
        self.assertEqual(len(errors), 1)
        self.assertIn("unclassified file under schemas: schemas/surprise.yaml", errors[0])

    def test_prefix_entries_classify_directories(self):
        nested = self.root / "conformance" / "valid"
        nested.mkdir(parents=True)
        (nested / "a.fhp.fasta").write_text("x\n")
        (nested / "b.fhr.fasta").write_text("x\n")
        prov = {"copied": [entry_for(b"x\n", "conformance/valid/a.fhp.fasta",
                                     "conformance/valid/a.fhp.fasta")],
                "legacy": [{"path": "conformance/"}], "owned": [],
                "strictDirs": ["conformance/valid"]}
        self.assertEqual(self.extras(prov), [])


if __name__ == "__main__":
    unittest.main()
