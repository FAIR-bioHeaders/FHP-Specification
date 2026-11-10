import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.make_provenance import PINNED_FILES, generate_entries


class MakeProvenanceTests(unittest.TestCase):
    def test_hashes_files_from_pinned_commit_including_tagged_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            upstream = Path(tmp)
            subprocess.run(["git", "init", "-q", str(upstream)], check=True)
            for path in PINNED_FILES:
                target = upstream / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(f"v0.5.0:{path}".encode())
            vector = upstream / "conformance/valid/fhp-fasta-test.fhp.fasta"
            vector.parent.mkdir(parents=True, exist_ok=True)
            vector.write_bytes(b"test vector")
            tagged_example = upstream / "examples/fhp/rich-predicted.fhp.yaml"
            tagged_bytes = tagged_example.read_bytes()
            subprocess.run(["git", "-C", str(upstream), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(upstream),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "v0.5.0",
                ],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(upstream), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            tagged_example.write_bytes(b"later main copy")

            entries = generate_entries(upstream, commit)

            self.assertIn(
                {
                    "local": "examples/fhp/rich-predicted.fhp.yaml",
                    "upstream": "examples/fhp/rich-predicted.fhp.yaml",
                    "sha256": hashlib.sha256(tagged_bytes).hexdigest(),
                },
                entries,
            )
            self.assertIn(
                {
                    "local": "tests/fixtures/releases/fhp-v0.5.0.json",
                    "upstream": "fhp.json",
                    "sha256": hashlib.sha256(b"v0.5.0:fhp.json").hexdigest(),
                },
                entries,
            )
            self.assertTrue(
                any(
                    entry["upstream"]
                    == "conformance/valid/fhp-fasta-test.fhp.fasta"
                    for entry in entries
                )
            )


if __name__ == "__main__":
    unittest.main()
