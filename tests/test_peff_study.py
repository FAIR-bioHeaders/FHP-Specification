# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Guard study byte identity and positive/negative evidence without external tools."""

import base64
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "studies" / "peff"


def load_runner():
    import importlib.util

    spec = importlib.util.spec_from_file_location("peff_run", ROOT / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PEFFRunnerPinTests(unittest.TestCase):
    """run.py checks external tools against their pins before executing them."""

    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        import subprocess

        return subprocess.run(
            ["git", "-C", str(self.tmp / "comet"), *args],
            check=True, capture_output=True, text=True,
            env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org",
                 "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
        ).stdout.strip()

    def test_sources_pin_the_validator_files_and_perl_module(self):
        sources = json.loads((ROOT / "sources.json").read_text())
        self.assertEqual(set(sources["validatorFiles"]),
                         {"bin/PEFF/validatePEFF", "var/CV/PSI-MOD.obo"})
        result = json.loads((ROOT / "results.json").read_text())
        for path, digest in sources["validatorFiles"].items():
            self.assertEqual(result["executableDigests"][Path(path).name], digest)
        self.assertEqual(sources["perlModules"]["JSON"]["version"], "4.11")
        self.assertRegex(sources["perlModules"]["JSON"]["sha256"], r"^[0-9a-f]{64}$")

    def test_archive_is_checked_before_extraction(self):
        import zipfile

        archive = self.tmp / "validator.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("bin/PEFF/validatePEFF", "#!/usr/bin/env perl\n")
        data = archive.read_bytes()
        pin = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        out = self.runner.verify_validator_archive(archive, pin, self.tmp / "ok")
        self.assertTrue((out / "bin/PEFF/validatePEFF").is_file())
        with self.assertRaises(RuntimeError):
            self.runner.verify_validator_archive(
                archive, dict(pin, sha256="0" * 64), self.tmp / "bad")
        self.assertFalse((self.tmp / "bad").exists())

    def test_comet_must_be_built_from_the_clean_pinned_checkout(self):
        (self.tmp / "comet").mkdir()
        self.git("init", "-q", ".")
        (self.tmp / "comet" / "source.cpp").write_text("int main() {}\n")
        self.git("add", ".")
        self.git("commit", "-qm", "pinned")
        binary = self.tmp / "comet" / "comet.exe"
        binary.write_bytes(b"binary")  # untracked build output is allowed
        pin = {"commit": self.git("rev-parse", "HEAD")}
        digest = self.runner.verify_comet(binary, pin)
        self.assertEqual(digest, hashlib.sha256(b"binary").hexdigest())
        self.assertEqual(self.runner.verify_comet(binary, pin, digest), digest)
        with self.assertRaises(RuntimeError):
            self.runner.verify_comet(binary, pin, "0" * 64)
        with self.assertRaises(RuntimeError):
            self.runner.verify_comet(binary, {"commit": "0" * 40})
        (self.tmp / "comet" / "source.cpp").write_text("int main() { return 1; }\n")
        with self.assertRaises(RuntimeError):
            self.runner.verify_comet(binary, pin)
        outside = self.tmp / "elsewhere"
        outside.mkdir()
        (outside / "comet.exe").write_bytes(b"binary")
        with self.assertRaises(RuntimeError):
            self.runner.verify_comet(outside / "comet.exe", pin)


class PEFFStudyTests(unittest.TestCase):
    def test_fixture_integrity_and_payload(self):
        manifest = json.loads((ROOT / "fixtures.json").read_text())
        plain = (ROOT / "plain.faa").read_bytes()
        self.assertEqual(len(manifest), 9)
        for name, entry in manifest.items():
            with self.subTest(name=name):
                content = (ROOT / name).read_bytes()
                self.assertEqual(len(content), entry["bytes"])
                self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])
                payload = content[content.index(b">syn:p1") :]
                if name == "fhp-tampered.faa":
                    self.assertNotEqual(payload, plain)
                else:
                    self.assertEqual(payload, plain)
                lines = content.splitlines(keepends=True)
                scalars = [line for line in lines if line.startswith(b";~checksum:")]
                if scalars:
                    self.assertEqual(len(scalars), 1)
                    digest = hashlib.new("sha512_256")
                    digest.update(
                        b"".join(line for line in lines if line not in scalars)
                    )
                    calculated = base64.b64encode(digest.digest()).decode()
                    self.assertEqual(calculated, entry["toolkitChecksum"])
                    asserted = scalars[0].decode().split(":", 1)[1].strip()
                    self.assertEqual(calculated == asserted, name != "fhp-tampered.faa")

    def test_reader_evidence_and_controls(self):
        result = json.loads((ROOT / "results.json").read_text())
        self.assertEqual(
            result["packages"], {"pyteomics": "5.0", "fair-bioheaders": "0.11.0"}
        )
        cases = result["cases"]
        baseline = cases["peff-only.faa"]["comet"]["peptides"]
        self.assertEqual(len(baseline), 10)
        self.assertIn("isValid=1\n", cases["peff-only.faa"]["validator"]["stdout"])
        for name, case in cases.items():
            with self.subTest(name=name):
                self.assertEqual(case["comet"]["exit"], 0)
                self.assertEqual(
                    case["comet"]["peptides"] == baseline, name != "fhp-tampered.faa"
                )
        for name in [
            "peff-before-fhp.faa",
            "fhp-inside-peff.faa",
            "peff-missing-prefix.faa",
            "peff-wrong-count.faa",
        ]:
            validator = cases[name]["validator"]
            self.assertEqual(validator["exit"], 0)
            self.assertIn("isValid=0\n", validator["stdout"])
        expected_sequences = ["MPEPTIDEKACDEFGHIKR", "MSTNPKPQRKTKRNTNR"]
        for name in ["peff-only.faa", "peff-before-fhp.faa", "fhp-inside-peff.faa"]:
            self.assertEqual(
                [row["sequence"] for row in cases[name]["pyteomics"]["records"]],
                expected_sequences,
            )
        self.assertEqual(
            cases["fhp-inside-peff.faa"]["pyteomics"]["databaseBlocks"], []
        )
        self.assertEqual(
            len(cases["peff-before-fhp.faa"]["pyteomics"]["databaseBlocks"]), 1
        )
        self.assertEqual(cases["fhp-tampered.faa"]["bioheaders"]["exit"], 1)
        self.assertIn(
            "Checksum verification failed",
            cases["fhp-tampered.faa"]["bioheaders"]["stderr"],
        )
        for name in [
            "fhp-only.faa",
            "fhp-before-peff.faa",
            "peff-before-fhp.faa",
            "fhp-inside-peff.faa",
        ]:
            self.assertEqual(cases[name]["bioheaders"]["exit"], 0)


if __name__ == "__main__":
    unittest.main()
