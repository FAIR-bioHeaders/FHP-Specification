"""Keep the reference form of this repository's schema review baselines honest.

FHP-Specification#31 acceptance item 5 (maintainer ruling, 2026-11-16): the FHR
review baseline's ``$id`` must stop naming a floating branch on the legacy FHR
development repository, because a released contract resolves at a tag or at that
tag's w3id alias and never at raw ``main`` (FAIR-bioHeaders-Specification#241).
``.github/schema-baseline-refs.json`` records the decision, the measurements and
the files deliberately left unchanged; this module is what stops those claims
from going slack afterwards.

Standard library only and offline by design: nothing here dereferences an ``$id``
because nothing in this repository does - every ``$ref`` in the contracts and
baselines is an internal absolute fragment, the validators build
``Draft202012Validator`` from locally read bytes without a resolver, and the
selection rules in ``docs/SCHEMA-VERSIONS.md`` (V1-V6) identify a contract by
string matching rather than by fetching. The guard therefore compares bytes and
parsed values that are already in the tree.
"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GITHUB = ROOT / ".github"
RECORD = GITHUB / "schema-baseline-refs.json"
DRIFT = ROOT / "scripts" / "check_schema_drift.py"

# An $id that names an immutable resource: the release's w3id alias, or the
# publication authority's raw URL at a tag or a full commit. A branch - "main"
# included - is never acceptable for released material (#241), and neither is a
# development repository's URL, which is where the legacy FHR-Specification
# string pointed.
W3ID_RELEASE = re.compile(
    r"^https://w3id\.org/fair-bioheaders/(?:fhr|fhp|fhgff3)/v[0-9]+\.[0-9]+\.[0-9]+/?$")
RAW_IMMUTABLE = re.compile(
    r"^https://raw\.githubusercontent\.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/"
    r"(?:v[0-9]+\.[0-9]+\.[0-9]+|[0-9a-f]{40})/(?:fhr|fhp|fhgff3)\.json$")
TAG = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def immutable_reference(url):
    return bool(W3ID_RELEASE.match(url) or RAW_IMMUTABLE.match(url))


def floating_references(directory):
    """{file name: $id} for every schema baseline in `directory` whose $id is not immutable."""
    found = {}
    for path in sorted(directory.glob("schema-baseline*.json")):
        if path.name == RECORD.name:
            continue  # the record is provenance, not a schema baseline
        dollar_id = load(path).get("$id")
        if dollar_id and not immutable_reference(dollar_id):
            found[path.name] = dollar_id
    return found


def run_drift(schema, baseline):
    return subprocess.run(
        [sys.executable, str(DRIFT), "--schema", str(schema), "--baseline", str(baseline)],
        cwd=ROOT, capture_output=True, text=True)


def drift_pointers(result):
    """The JSON pointers the drift check reported, ignoring its banner and advice lines.

    The banner names absolute paths (so it also starts with "/"); the only marker
    that distinguishes a pointer line is that it is not the "differs from" header.
    """
    return [line for line in result.stderr.splitlines()
            if line.startswith("/") and " differs from " not in line]


class FhrBaselineReferenceTests(unittest.TestCase):
    """The ruled change itself: the FHR baseline's $id is the recorded immutable alias."""

    @classmethod
    def setUpClass(cls):
        cls.record = load(RECORD)
        cls.entry = next(e for e in cls.record["baselines"]
                         if e["local"] == ".github/schema-baseline.json")
        cls.baseline = load(GITHUB / "schema-baseline.json")

    def test_dollar_id_is_the_recorded_immutable_alias(self):
        dollar_id = self.baseline["$id"]
        self.assertEqual(dollar_id, self.entry["authority"]["citation"])
        self.assertEqual(dollar_id, "https://w3id.org/fair-bioheaders/fhr/v0.3.1")
        self.assertTrue(immutable_reference(dollar_id), dollar_id)

    def test_no_branch_and_no_legacy_development_repository(self):
        dollar_id = self.baseline["$id"]
        self.assertNotIn("/main/", dollar_id)
        self.assertNotIn("FHR-Specification", dollar_id)
        self.assertNotEqual(dollar_id, self.entry["dollarId"]["before"])

    def test_the_alias_resolves_to_the_bytes_this_snapshot_holds(self):
        """Internal consistency of the record, without fetching: alias == tag == tree."""
        authority = self.entry["authority"]
        tag = self.record["fhrReleaseLine"]["tags"][authority["ref"]]
        self.assertTrue(TAG.match(authority["ref"]), authority["ref"])
        self.assertTrue(SHA1.match(authority["commit"]))
        self.assertTrue(SHA1.match(authority["tagObject"]))
        self.assertEqual(authority["commit"], tag["commit"])
        self.assertEqual(authority["tagObject"], tag["tagObject"])
        self.assertEqual(authority["pinnedSourceUrl"],
                         "https://raw.githubusercontent.com/FAIR-bioHeaders/"
                         f"FAIR-bioHeaders-Specification/{authority['ref']}/fhr.json")
        self.assertTrue(immutable_reference(authority["pinnedSourceUrl"]))
        # The snapshot's value, the frozen copy's value and the release's bytes.
        reviewed = self.entry["reviewedSchema"]
        fhr = (ROOT / "fhr.json").read_bytes()
        self.assertEqual(reviewed["size"], len(fhr))
        self.assertEqual(reviewed["sha256"], hashlib.sha256(fhr).hexdigest())
        self.assertEqual(authority["sha256"], reviewed["sha256"])
        self.assertEqual(tag["sha256"], reviewed["sha256"])
        self.assertEqual(authority["size"], len(fhr))
        self.assertEqual(self.entry["dollarId"]["baselineBytesAfter"]["sha256"],
                         hashlib.sha256((GITHUB / "schema-baseline.json").read_bytes()).hexdigest())

    def test_the_baseline_is_still_the_frozen_copy_modulo_identity(self):
        """Only $id may differ from fhr.json, so a constraint change cannot hide in the retarget."""
        baseline, schema = dict(self.baseline), load(ROOT / "fhr.json")
        self.assertIn("$id", baseline)
        self.assertNotEqual(baseline["$id"], schema["$id"])  # the sanctioned divergence
        del baseline["$id"]
        del schema["$id"]
        self.assertEqual(canonical(baseline), canonical(schema))

    def test_the_retired_fhr_drift_pair_reports_the_one_intentional_pointer(self):
        """check_schema_drift.py compares $id too; the divergence is exactly one pointer, /$id."""
        result = run_drift(ROOT / "fhr.json", GITHUB / "schema-baseline.json")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(drift_pointers(result), [
            '/$id: "https://w3id.org/fair-bioheaders/fhr/v0.3.1" -> '
            '"https://raw.githubusercontent.com/FAIR-bioHeaders/FHR-Specification/main/fhr.json"'])
        self.assertIn("schema-baseline.json", result.stderr)

    def test_update_would_restore_the_legacy_string_and_the_guard_notices(self):
        """--update on the retired pair rewrites the $id back; the inventory test must catch it."""
        with tempfile.TemporaryDirectory() as name:
            workdir = Path(name) / "FhpBaselineRefsUpdateControl"  # exact case: no FS fallback
            workdir.mkdir()
            legacy = dict(self.baseline)
            legacy["$id"] = self.entry["dollarId"]["before"]
            (workdir / "schema-baseline.json").write_text(
                json.dumps(legacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self.assertEqual(floating_references(workdir),
                             {"schema-baseline.json": self.entry["dollarId"]["before"]})

    def test_a_fresh_canonical_snapshot_of_the_frozen_copy_is_still_flagged(self):
        """Negative control for the classifier itself: it is not vacuously green."""
        with tempfile.TemporaryDirectory() as name:
            workdir = Path(name) / "FhpBaselineRefsImmutableControl"
            workdir.mkdir()
            good = dict(self.baseline)
            good["$id"] = ("https://raw.githubusercontent.com/FAIR-bioHeaders/"
                           "FAIR-bioHeaders-Specification/v0.3.1/fhr.json")
            (workdir / "schema-baseline.json").write_text(json.dumps(good), encoding="utf-8")
            self.assertEqual(floating_references(workdir), {})
            for bad in ("https://w3id.org/fair-bioheaders/fhr/v0.3",           # not three numbers
                        "https://w3id.org/fair-bioheaders/fhr/latest",
                        "https://example.org/fhr.json"):
                with self.subTest(dollar_id=bad):
                    probe = dict(good)
                    probe["$id"] = bad
                    (workdir / "schema-baseline-fhp.json").write_text(
                        json.dumps(probe), encoding="utf-8")
                    self.assertIn("schema-baseline-fhp.json", floating_references(workdir))
                    (workdir / "schema-baseline-fhp.json").unlink()


class UndivergedPairTests(unittest.TestCase):
    """The two baselines this PR deliberately did NOT touch stay exact pairs of their schemas."""

    def test_fhp_pair_is_still_exact_and_is_the_live_ci_gate(self):
        result = run_drift(ROOT / "fhp.json", GITHUB / "schema-baseline-fhp.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(load(GITHUB / "schema-baseline-fhp.json")["$id"],
                         "https://raw.githubusercontent.com/FAIR-bioHeaders/"
                         "FAIR-bioHeaders-Specification/main/fhp.json")

    def test_fhgff3_pair_is_still_exact(self):
        result = run_drift(ROOT / "fhgff3.json", GITHUB / "schema-baseline-fhgff3.json")
        self.assertEqual(result.returncode, 0, result.stderr)


class RecordIntegrityTests(unittest.TestCase):
    """The record stays a record: no branch for released material, and honest about drafts."""

    @classmethod
    def setUpClass(cls):
        cls.record = load(RECORD)

    def test_every_recorded_release_resolves_a_tag_to_a_commit(self):
        tags = self.record["fhrReleaseLine"]["tags"]
        self.assertTrue(tags)
        for name, entry in tags.items():
            with self.subTest(tag=name):
                self.assertTrue(TAG.match(name), name)
                self.assertTrue(SHA1.match(entry["commit"]), entry["commit"])
                self.assertTrue(SHA1.match(entry["tagObject"]), entry["tagObject"])
                self.assertEqual(entry["path"], "fhr.json")  # root, not schemas/
                self.assertGreater(entry["size"], 0)
                self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(tags["v0.6.0"]["commit"],
                         "0ae18b00ee4bd71ab2dc28bae706b0f9d195076b")
        self.assertEqual(tags["v0.3.1"]["commit"],
                         "378b534dda9c1d759f25b4b32287172402492233")

    def test_the_schemas_path_is_recorded_as_not_a_contract_location(self):
        self.assertIn("404", self.record["authority"]["pathNote"])
        self.assertIn("ROOT", self.record["authority"]["pathNote"])

    def test_floating_references_are_exactly_the_known_exceptions(self):
        known = {Path(e["local"]).name: e["dollarId"] for e in self.record["knownExceptions"]}
        self.assertEqual(floating_references(GITHUB), known)
        self.assertNotIn("schema-baseline.json", known)  # the FHR baseline is fixed

    def test_the_record_makes_no_draft_claim(self):
        """Rule V7: this record is about released FHR bytes; FHT and FHGM stay drafts."""
        structural = json.dumps({
            "citation": self.record["baselines"][0]["authority"]["citation"],
            "pinnedSourceUrl": self.record["baselines"][0]["authority"]["pinnedSourceUrl"],
            "tags": {k: v["commit"] for k, v in
                     self.record["fhrReleaseLine"]["tags"].items()},
        })
        for forbidden in ("FHT", "FHGM", "fht.json", "fhgm"):
            self.assertNotIn(forbidden, structural)
        self.assertIn("V7", self.record["v7Statement"])
        self.assertIn("draft", self.record["v7Statement"])

    def test_the_dispositions_say_what_was_left_unchanged_and_why(self):
        by_local = {e["local"]: e for e in self.record["baselines"]}
        for local in (".github/schema-baseline-fhp.json", ".github/schema-baseline-fhgff3.json"):
            with self.subTest(local=local):
                self.assertEqual(by_local[local]["disposition"],
                                 "unchanged in this PR - reported")
                self.assertGreater(len(by_local[local]["reason"]), 200)
        self.assertEqual(by_local[".github/schema-baseline.json"]["dollarId"]["before"],
                         "https://raw.githubusercontent.com/FAIR-bioHeaders/"
                         "FHR-Specification/main/fhr.json")


if __name__ == "__main__":
    unittest.main()
