"""Exercise the FHP-owned conformance vectors, their generator and their checker.

The package (docs/DEVELOPMENT-TREE.md Q4, FAIR-bioHeaders/FHP-Specification#2)
covers the fhp-fasta set and the FASTA-container R-rule vectors; the complete
family manifest runs from the pinned shared tree in shared-parity.yml.
"""

import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance"


def run(*arguments):
    return subprocess.run([sys.executable, *map(str, arguments)], capture_output=True, text=True)


class ConformanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.manifest = json.loads((CONFORMANCE / "manifest.json").read_text())

    def check(self, *extra, conformance=CONFORMANCE):
        return run(ROOT / "scripts/check_conformance.py", "--conformance", conformance, *extra)

    def copy_vectors(self):
        copy = self.root / "conformance"
        shutil.copytree(CONFORMANCE, copy)
        return copy

    def test_committed_vectors_pass_stdlib_and_schema_checks(self):
        result = self.check("--schema")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok: vectors match the generator", result.stdout)
        self.assertIn("ok: valid metadata matches fhr.json (fhp.json for FHP)", result.stdout)

    def test_generator_is_deterministic(self):
        outputs = [self.root / "first", self.root / "second"]
        for output in outputs:
            result = run(ROOT / "scripts/make_conformance.py", "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
        first, second = ({path.relative_to(output): path.read_bytes()
                          for path in output.rglob("*") if path.is_file()} for output in outputs)
        self.assertEqual(first, second)

    def test_modified_vector_is_reported(self):
        copy = self.copy_vectors()
        vector = copy / "valid/fasta-lf.fhr.fasta"
        vector.write_bytes(vector.read_bytes().replace(b"ACGT", b"ACGA", 1))
        result = self.check(conformance=copy)
        self.assertEqual(result.returncode, 1)
        self.assertIn("valid/fasta-lf.fhr.fasta: differs from the generator output", result.stderr)
        self.assertIn("fasta-lf: manifest", result.stderr)

    def test_line_ending_normalization_is_reported(self):
        copy = self.copy_vectors()
        vector = copy / "valid/fasta-crlf.fhr.fasta"
        vector.write_bytes(vector.read_bytes().replace(b"\r\n", b"\n"))
        result = self.check("--skip-regeneration", conformance=copy)
        self.assertEqual(result.returncode, 1)
        self.assertIn("fasta-crlf: manifest", result.stderr)

    def test_extra_file_is_reported(self):
        copy = self.copy_vectors()
        (copy / "invalid/stray.fhr.fasta").write_bytes(b">x\nA\n")
        result = self.check(conformance=copy)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid/stray.fhr.fasta: not produced by the generator", result.stderr)

    def test_legacy_family_files_are_out_of_the_regeneration_scope(self):
        # The frozen pre-v0.5.0 family vectors (GFA, microdata, JSON-LD, FHGFF3)
        # stay on disk but this generator does not produce them; only
        # FASTA-container files are compared (Q4).
        copy = self.copy_vectors()
        (copy / "invalid/extra-legacy.fhr.gfa").write_bytes(b"#~genome: x\n")
        result = self.check(conformance=copy)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("extra-legacy.fhr.gfa", result.stderr)

    def test_pinned_vectors_match_provenance(self):
        # Every fhp-fasta vector the manifest runs at a copied[] path is the
        # byte-for-byte v0.5.0 shared copy the parity check digests.
        import hashlib
        copied = {entry["local"]: entry
                  for entry in json.loads((ROOT / "provenance.json").read_text())["copied"]}
        vectors = [v for v in self.manifest["vectors"] if v["format"] == "fhp-fasta"]
        pinned = [v for v in vectors if f"conformance/{v['file']}" in copied]
        self.assertEqual(len(pinned), 31)  # the full v0.5.0 set; 32nd is FHP-owned
        for vector in pinned:
            entry = copied[f"conformance/{vector['file']}"]
            data = (CONFORMANCE / vector["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], vector["id"])

    def test_every_rule_is_labelled_and_covered(self):
        labels = [label for document in ("docs/FORMAT.md", "docs/MICRODATA.md", "docs/JSONLD.md",
                                         "docs/FHP.md", "docs/FHGFF3.md", "docs/SCHEMA-VERSIONS.md")
                  for label in re.findall(r"\[([RMJPGV]\d+)\]", (ROOT / document).read_text())]
        self.assertEqual(labels, list(self.manifest["rules"]))
        for rule, details in self.manifest["rules"].items():
            outcomes = {
                vector["expected"] for vector in self.manifest["vectors"]
                if rule in vector.get("rules", [vector.get("rule")])
            }
            if "notApplicable" in details:
                # No invalid input exists (a writer rule or a recommendation),
                # or the rule's other side belongs to the family manifest (Q4);
                # valid vectors may cite it.
                self.assertNotIn("invalid", outcomes, rule)
            else:
                self.assertEqual(outcomes, {"valid", "invalid"}, rule)

    def test_manifest_fields(self):
        for vector in self.manifest["vectors"]:
            self.assertIn(vector["format"], {"fasta", "fhp-fasta"})
            self.assertTrue((CONFORMANCE / vector["file"]).is_file(), vector["file"])
            self.assertEqual(vector["file"].split("/")[0], vector["expected"])
            if vector["expected"] == "valid":
                self.assertRegex(vector["checksum"], r"^[A-Za-z0-9+/]{43}=$")
                subject = "proteome" if vector["format"] == "fhp-fasta" else "genome"
                self.assertTrue({subject, "version"} <= vector["metadata"].keys())
            else:
                self.assertIn(vector["rule"], self.manifest["rules"])
                self.assertTrue(vector["reason"])

    def test_fhp_vectors(self):
        """specs/006-protein-header contracts/conformance.md."""
        vectors = {v["id"]: v for v in self.manifest["vectors"] if v["format"] == "fhp-fasta"}
        self.assertEqual(self.manifest["fhpSpecification"], "docs/FHP.md")
        self.assertEqual(len([v for v in vectors.values() if v["expected"] == "valid"]), 13)
        self.assertEqual(len([v for v in vectors.values() if v["expected"] == "invalid"]), 19)
        self.assertEqual(vectors["fhp-fasta-author-bad-name-type"]["rule"], "P1")
        # The Q4 package: the complete v0.5.0 fhp-fasta set is present locally.
        for vector_id in ("fhp-fasta-escaped-record-markers", "fhp-fasta-extension-fields",
                          "fhp-fasta-extension-nested", "fhp-fasta-extension-older-release",
                          "fhp-fasta-extension-older-version", "fhp-fasta-rich",
                          "fhp-fasta-schema-canonical-raw-main", "fhp-fasta-schema-raw-tag",
                          "fhp-fasta-schema-release-without-type"):
            self.assertIn(vector_id, vectors)
        self.assertEqual(vectors["fhp-fasta-extension-fields"]["rules"], ["R15", "P1"])
        self.assertEqual(vectors["fhp-fasta-schema-release-without-type"]["rule"], "V4")
        self.assertEqual(vectors["fhp-fasta-schema-release-without-type"]["result"],
                         "unsupported-version")
        for vector in vectors.values():
            self.assertTrue(vector["file"].endswith(".fhp.fasta")
                            or vector["file"].endswith(".fhp.fasta.gz"), vector["file"])
        body = (CONFORMANCE / vectors["fhp-fasta-lf"]["file"]).read_bytes().split(b"\n>", 1)[1]
        for residue in (b"*", b"U", b"O", b"B", b"Z", b"J", b"X", b"m", b"-"):
            self.assertIn(residue, body)
        for vector in vectors.values():
            if vector["expected"] == "invalid" and vector["rule"] in {"P1", "P2"}:
                self.assertIn("metadata", vector, vector["id"])
        self.assertEqual(vectors["fhp-fasta-cites-fhr-schema"]["rule"], "P2")

    def test_compressed_vectors_share_the_plain_checksum(self):
        vectors = {vector["id"]: vector for vector in self.manifest["vectors"]}
        compressed = [vector for vector in vectors.values()
                      if vector["compressed"] and vector["expected"] == "valid"]
        self.assertGreaterEqual(len(compressed), 4)
        for vector in compressed:
            kind = vector["format"]
            plain = vectors[f"{kind}-lf"]
            data = (CONFORMANCE / vector["file"]).read_bytes()
            self.assertEqual(data[3] & 0x08, 0, "no stored file name")
            self.assertEqual(data[4:8], b"\0\0\0\0", "mtime 0")
            self.assertEqual(gzip.decompress(data), (CONFORMANCE / plain["file"]).read_bytes())
            self.assertEqual(vector["checksum"], plain["checksum"])

    def test_converter_that_accepts_everything_fails(self):
        bin_directory = self.root / "bin"
        bin_directory.mkdir()
        for name in ("fhr-fasta-validate", "fhr-gfa-validate"):
            script = bin_directory / name
            script.write_text(f"#!{sys.executable}\nraise SystemExit(0)\n")
            script.chmod(0o755)
        # Unused by the FHP-owned manifest, but converter_commands requires it.
        script = bin_directory / "fhr-convert"
        script.write_text(f"#!{sys.executable}\nraise SystemExit(1)\n")
        script.chmod(0o755)
        result = self.check("--skip-regeneration", "--converter", bin_directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("fasta-u2028-in-header: converter accepted; expected invalid, R6",
                      result.stderr)
        self.assertIn("fhp-fasta-missing-source-type: converter accepted; "
                      "expected invalid, P1", result.stderr)
        self.assertIn("fhp-fasta-schema-release-without-type: converter accepted; "
                      "expected invalid, V4", result.stderr)
        self.assertNotIn("fasta-lf:", result.stderr)
        self.assertNotIn("fhp-fasta-lf:", result.stderr)

    def test_converter_without_a_format_is_skipped_unless_required(self):
        # The skip/require mechanism, exercised on a synthetic tree: the
        # FHP-owned manifest holds only FASTA-container vectors, so a fake
        # JSON-LD vector is appended to the copied manifest. The fake
        # converter is correct on every format except JSON-LD, which it
        # rejects as an unsupported file extension (as fhr 0.3.3 does).
        copy = self.copy_vectors()
        (copy / "valid").mkdir(exist_ok=True)
        extra = {"id": "jsonld-canonical-embedded", "file": "valid/jsonld-canonical-embedded"
                 ".fhr.jsonld", "format": "jsonld", "compressed": False, "expected": "valid",
                 "rules": ["J1"], "description": "synthetic mechanism probe", "metadata": {}}
        manifest = json.loads((copy / "manifest.json").read_text())
        manifest["vectors"].append(extra)
        (copy / "manifest.json").write_text(json.dumps(manifest))
        (copy / extra["file"]).write_text("{}\n")
        bin_directory = self.root / "bin"
        bin_directory.mkdir()
        all_vectors = json.dumps({v["file"]: v for v in manifest["vectors"]})
        body = (
            f"#!{sys.executable}\nimport json, sys\n"
            f"vectors = {{v.rsplit('/', 1)[-1]: m for v, m in json.loads({all_vectors!r}).items()}}\n"
            "vector = vectors[sys.argv[1].rsplit('/', 1)[-1]]\n"
            "if vector['format'] == 'jsonld':\n"
            "    print('FHR: Unsupported file extension: ' + sys.argv[1], file=sys.stderr)\n"
            "    raise SystemExit(1)\n"
            "if vector['expected'] != 'valid':\n"
            "    raise SystemExit(1)\n"
            "if len(sys.argv) > 2:\n"
            "    json.dump(vector['metadata'], open(sys.argv[2], 'w'))\n"
        )
        for name in ("fhr-fasta-validate", "fhr-gfa-validate", "fhr-convert"):
            script = bin_directory / name
            script.write_text(body)
            script.chmod(0o755)
        lenient = self.check("--skip-regeneration", "--converter", bin_directory, conformance=copy)
        self.assertEqual(lenient.returncode, 0, lenient.stderr)
        self.assertIn("(1 vectors left out: jsonld not supported by this converter)",
                      lenient.stdout)
        strict = self.check("--skip-regeneration", "--require-format", "jsonld",
                            "--converter", bin_directory, conformance=copy)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("jsonld-canonical-embedded: converter rejected (FHR: Unsupported file "
                      "extension", strict.stderr)

    @unittest.skipUnless(os.environ.get("FHR_CONVERTER"), "set FHR_CONVERTER to test a converter")
    def test_converter_agrees_with_manifest(self):
        result = self.check("--skip-regeneration", "--converter", os.environ["FHR_CONVERTER"])
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
