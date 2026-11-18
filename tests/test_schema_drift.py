"""Ensure schema changes cannot pass unnoticed, including nested constraints."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SchemaDriftTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.schema = self.root / "fhr.json"
        self.baseline = self.root / "baseline.json"
        self.original = json.loads((ROOT / "fhr.json").read_text())
        self.write_schema(self.original)
        self.baseline.write_text(json.dumps(self.original))

    def write_schema(self, value):
        self.schema.write_text(json.dumps(value))

    def run_command(self, *extra):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_schema_drift.py"),
             "--schema", str(self.schema), "--baseline", str(self.baseline), *extra],
            cwd=self.root, capture_output=True, text=True,
        )

    def test_formatting_and_object_order_are_ignored(self):
        self.schema.write_text(json.dumps(dict(reversed(list(self.original.items()))), indent=4))
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_constraints_and_metadata_changes_fail(self):
        changes = [
            (lambda s: s["required"].remove("checksum"), "/required"),
            (lambda s: s["properties"]["dateCreated"].update(format="date-time"),
             "/properties/dateCreated/format"),
            (lambda s: s["definitions"]["sha2"].update(minLength=1),
             "/definitions/sha2/minLength"),
            (lambda s: s.update(additionalProperties=True), "/additionalProperties"),
            (lambda s: s["properties"].update(newField={"type": "string"}),
             "/properties/newField"),
            (lambda s: s.update(description="changed"), "/description"),
        ]
        for mutate, pointer in changes:
            with self.subTest(pointer=pointer):
                instance = json.loads(json.dumps(self.original))
                mutate(instance)
                self.write_schema(instance)
                result = self.run_command()
                self.assertEqual(result.returncode, 1)
                self.assertIn(pointer, result.stderr)
                self.assertEqual(json.loads(self.baseline.read_text()), self.original)

    def test_boolean_is_distinct_from_number(self):
        self.baseline.write_text('{"minimum": 1}')
        self.schema.write_text('{"minimum": true}')
        result = self.run_command()
        self.assertEqual(result.returncode, 1)
        self.assertIn('/minimum: 1 -> true', result.stderr)

    def test_intentional_update_is_explicit(self):
        self.original["properties"]["newField"] = {"type": "string"}
        self.write_schema(self.original)
        self.assertEqual(self.run_command().returncode, 1)
        result = self.run_command("--update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_command().returncode, 0)
        self.assertEqual(json.loads(self.baseline.read_text()), self.original)

    def test_missing_baseline_fails(self):
        self.baseline.unlink()
        result = self.run_command()
        self.assertEqual(result.returncode, 1)
        self.assertIn("baseline.json", result.stderr)

    def test_invalid_json_duplicate_keys_and_constants_fail(self):
        for invalid in ('{', '{"type":"object","type":"string"}', '{"minimum":NaN}'):
            with self.subTest(invalid=invalid):
                self.schema.write_text(invalid)
                result = self.run_command()
                self.assertEqual(result.returncode, 1)
                self.assertIn("Schema drift check failed", result.stderr)



class RepositoryDefaultsTests(unittest.TestCase):
    """The bare command checks the FHP pair CI gates; frozen baselines stay frozen (#36)."""

    def run_script(self, *extra):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_schema_drift.py"), *extra],
            cwd=ROOT, capture_output=True, text=True,
        )

    def test_bare_command_checks_the_fhp_pair(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fhp.json: matches the schema baseline", result.stdout)

    def test_update_refuses_the_frozen_baselines(self):
        for schema, baseline in (("fhr.json", ".github/schema-baseline.json"),
                                 ("fhgff3.json", ".github/schema-baseline-fhgff3.json")):
            with self.subTest(baseline=baseline):
                before = (ROOT / baseline).read_bytes()
                result = self.run_script("--schema", str(ROOT / schema),
                                         "--baseline", str(ROOT / baseline), "--update")
                self.assertEqual(result.returncode, 1)
                self.assertIn("Refusing to update", result.stderr)
                self.assertIn("#36", result.stderr)
                self.assertEqual((ROOT / baseline).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
