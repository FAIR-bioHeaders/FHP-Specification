import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

import scripts.make_provenance as mp
from scripts.make_provenance import ADJUSTMENTS, PINNED_FILES, generate_entries


def git(cwd, *args, **kwargs):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True,
                          capture_output=True, text=True,
                          env={"GIT_AUTHOR_NAME": "Test",
                               "GIT_AUTHOR_EMAIL": "test@example.org",
                               "GIT_COMMITTER_NAME": "Test",
                               "GIT_COMMITTER_EMAIL": "test@example.org",
                               "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
                          **kwargs).stdout.strip()


class MakeProvenanceTests(unittest.TestCase):
    def commit_tree(self, message):
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-qm", message)
        return git(self.upstream, "rev-parse", "HEAD")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.upstream = Path(self._tmp.name)
        git(self.upstream, "init", "-q", ".")
        for path in PINNED_FILES:
            target = self.upstream / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if path == "fhp_linkml.yml":
                # A stand-in for the shared model: the retarget line must exist
                # exactly once for the adjustment to apply.
                target.write_text("imports:\n- linkml:types\n- schemas/core\n- schemas/shared\n")
            else:
                target.write_bytes(f"v0.5.0:{path}".encode())
        vector = self.upstream / "conformance/valid/fhp-fasta-test.fhp.fasta"
        vector.parent.mkdir(parents=True, exist_ok=True)
        vector.write_bytes(b"test vector")
        gzipped = self.upstream / "conformance/valid/fhp-fasta-bgzf-test.fhp.fasta.gz"
        gzipped.write_bytes(b"\x1f\x8b test gzip vector")
        self.commit = self.commit_tree("v0.5.0")
        # In the synthetic upstream the companion fix and the v0.6.0 contract
        # commit are the same commit unless a test adds another one.
        self._saved_companion = mp.COMPANION_COMMIT
        self._saved_contract = mp.CONTRACT_COMMIT
        mp.COMPANION_COMMIT = self.commit
        mp.CONTRACT_COMMIT = self.commit

    def tearDown(self):
        mp.COMPANION_COMMIT = self._saved_companion
        mp.CONTRACT_COMMIT = self._saved_contract
        self._tmp.cleanup()

    def set_contract(self, fhp_bytes):
        """A second upstream commit carrying the v0.6.0 contract chain (#31)."""
        (self.upstream / "fhp.json").write_bytes(fhp_bytes)
        (self.upstream / "fhp_linkml.yml").write_bytes(
            b"imports:\n- linkml:types\n- schemas/core\n- schemas/shared\n"
            b"# 1.2 model\n")
        (self.upstream / "schemas/shared.yaml").write_bytes(b"# widened #170\n")
        (self.upstream / "schemas/versions.json").write_bytes(b'{"current":"v0.6.0"}\n')
        mp.CONTRACT_COMMIT = self.commit_tree("v0.6.0")
        return mp.CONTRACT_COMMIT

    def set_companion(self, rich_bytes):
        """A companion-fix commit changing the tagged example (shared #201)."""
        example = self.upstream / "examples/fhp/rich-predicted.fhp.yaml"
        example.write_bytes(rich_bytes)
        mp.COMPANION_COMMIT = self.commit_tree("companion fix")
        return mp.COMPANION_COMMIT

    def entries(self, **kwargs):
        return generate_entries(self.upstream, self.commit, **kwargs)

    def test_hashes_files_from_pinned_commit(self):
        entries = self.entries()
        by_local = {entry["local"]: entry for entry in entries}
        digest = hashlib.sha256(b"v0.5.0:docs/FHP.md").hexdigest()
        self.assertEqual(by_local["docs/FHP.md"],
                         {"local": "docs/FHP.md", "upstream": "docs/FHP.md",
                          "size": len(b"v0.5.0:docs/FHP.md"), "sha256": digest})
        self.assertIn("schemas/versions.json", by_local)
        self.assertIn("docs/SCHEMA-VERSIONS.md", by_local)
        # docs/FORMAT.md joined the pinned set with the FHP-owned conformance
        # package (Q4, FHP-Specification#2): the package's rule vocabulary
        # needs its v0.5.0 [R11]-[R15] tokens at the pinned bytes.
        self.assertIn("docs/FORMAT.md", by_local)
        self.assertNotIn("conformance/manifest.json", by_local)  # FHP-owned, generated here

    def test_fhp_json_pin_serves_the_contract_and_the_release_fixtures(self):
        by_local = {entry["local"]: entry for entry in self.entries()}
        digest = hashlib.sha256(b"v0.5.0:fhp.json").hexdigest()
        for local in ("fhp.json", "tests/fixtures/releases/fhp-v0.5.0.json",
                      "tests/fixtures/releases/fhp-v0.6.0.json"):
            self.assertEqual(by_local[local]["upstream"], "fhp.json")
            self.assertEqual(by_local[local]["sha256"], digest)

    def test_contract_chain_repin_moves_only_the_fhp_contract_files(self):
        """FHP-Specification#31: the contract chain follows the v0.6.0 commit
        by per-entry override; every other copied entry, and the immutable
        v0.5.0 release fixture, keep the v0.5.0 bytes."""
        contract = self.set_contract(b"v0.6.0:fhp.json")
        by_local = {entry["local"]: entry for entry in self.entries()}
        contract_digest = hashlib.sha256(b"v0.6.0:fhp.json").hexdigest()
        v050_digest = hashlib.sha256(b"v0.5.0:fhp.json").hexdigest()
        for local in ("fhp.json", "tests/fixtures/releases/fhp-v0.6.0.json"):
            entry = by_local[local]
            self.assertEqual(entry["sha256"], contract_digest, local)
            self.assertEqual(entry["commit"], contract, local)
            self.assertIn("#31", entry["commitNote"])
        old = by_local["tests/fixtures/releases/fhp-v0.5.0.json"]
        self.assertEqual(old["sha256"], v050_digest)
        self.assertNotIn("commit", old)  # immutable: it stays at the base commit
        for local in ("fhp_linkml.yml", "schemas/shared-v0.6.yaml",
                      "schemas/versions.json"):
            self.assertEqual(by_local[local]["commit"], contract, local)
        self.assertNotIn("commit", by_local["docs/FHP.md"])
        self.assertNotIn("commit", by_local["schemas/shared.yaml"])
        self.assertNotIn("commit", by_local["conformance/valid/fhp-fasta-test.fhp.fasta"])
        # The model override keeps the import-retarget adjustment working on the
        # new upstream bytes, recording both digests.
        model = by_local["fhp_linkml.yml"]
        self.assertEqual(model["upstreamSha256"], hashlib.sha256(
            (self.upstream / "fhp_linkml.yml").read_bytes()).hexdigest())
        self.assertEqual(model["adjustment"]["kind"], "import-retarget")

    def test_model_copy_carries_the_machine_checkable_import_retarget(self):
        by_local = {entry["local"]: entry for entry in self.entries()}
        entry = by_local["fhp_linkml.yml"]
        upstream_digest = hashlib.sha256(
            (self.upstream / "fhp_linkml.yml").read_bytes()).hexdigest()
        self.assertEqual(entry["upstreamSha256"], upstream_digest)
        self.assertEqual(entry["adjustment"]["kind"], "import-retarget")
        self.assertNotEqual(entry["sha256"], upstream_digest)
        local = mp.apply_adjustment((self.upstream / "fhp_linkml.yml").read_bytes(),
                                    entry["adjustment"])
        self.assertEqual(hashlib.sha256(local).hexdigest(), entry["sha256"])
        self.assertIn(b"- schemas/core-v0.5\n", local)
        self.assertIn(b"- schemas/shared-v0.6\n", local)

    def test_shared_snapshot_is_vendored_at_the_contract_commit(self):
        """#31: schemas/shared.yaml stays at the package commit for the frozen
        FHGFF3 generation; the FHP 1.2 model reads the v0.6.0 snapshot."""
        contract = self.set_contract(b"v0.6.0:fhp.json")
        by_local = {entry["local"]: entry for entry in self.entries()}
        plain = by_local["schemas/shared.yaml"]
        snapshot = by_local["schemas/shared-v0.6.yaml"]
        self.assertNotIn("commit", plain)
        self.assertEqual(plain["sha256"],
                         hashlib.sha256(b"v0.5.0:schemas/shared.yaml").hexdigest())
        self.assertEqual(snapshot["commit"], contract)
        self.assertEqual(snapshot["upstreamSha256"],
                         hashlib.sha256(b"# widened #170\n").hexdigest())
        self.assertEqual(snapshot["adjustment"]["kind"], "provenance-header")
        self.assertEqual(snapshot["sha256"], hashlib.sha256(
            mp.SHARED_V06_HEADER.encode() + b"# widened #170\n").hexdigest())

    def test_core_snapshot_gets_the_provenance_header(self):
        by_local = {entry["local"]: entry for entry in self.entries()}
        entry = by_local["schemas/core-v0.5.yaml"]
        raw = (self.upstream / "schemas/core.yaml").read_bytes()
        self.assertEqual(entry["upstream"], "schemas/core.yaml")
        self.assertEqual(entry["upstreamSha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(entry["sha256"],
                         hashlib.sha256(mp.CORE_V05_HEADER.encode() + raw).hexdigest())
        self.assertEqual(entry["adjustment"]["kind"], "provenance-header")
        # An explicit root-core target (if Q2 later retires the v0.3-era core)
        # pins the plain payload instead.
        plain = {e["local"]: e for e in self.entries(core_target="schemas/core.yaml")}
        self.assertEqual(plain["schemas/core.yaml"]["sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertNotIn("adjustment", plain["schemas/core.yaml"])

    def test_companion_commit_pins_the_post_tag_example(self):
        self.set_companion(b"later main copy\n")
        by_local = {entry["local"]: entry for entry in self.entries()}
        entry = by_local["examples/fhp/rich-predicted.fhp.yaml"]
        self.assertEqual(entry["commit"], mp.COMPANION_COMMIT)
        self.assertEqual(entry["sha256"], hashlib.sha256(b"later main copy\n").hexdigest())
        self.assertIn("companion", entry["commitNote"])
        # All other entries stay on the tagged commit.
        self.assertNotIn("commit", by_local["docs/FHP.md"])

    def test_fhp_vectors_are_pinned_including_gzip(self):
        by_local = {entry["local"]: entry for entry in self.entries()}
        plain = by_local["conformance/valid/fhp-fasta-test.fhp.fasta"]
        self.assertEqual(plain["sha256"], hashlib.sha256(b"test vector").hexdigest())
        gz = by_local["conformance/valid/fhp-fasta-bgzf-test.fhp.fasta.gz"]
        self.assertEqual(gz["sha256"], hashlib.sha256(b"\x1f\x8b test gzip vector").hexdigest())

    def test_retarget_refuses_upstream_bytes_without_the_line(self):
        with self.assertRaises(ValueError):
            mp.apply_adjustment(b"no imports here", ADJUSTMENTS[("fhp_linkml.yml", "fhp_linkml.yml")])


if __name__ == "__main__":
    unittest.main()
