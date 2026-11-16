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
