"""Current-source normalization and refusal controls; no network dependency."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reference_port', ROOT / 'scripts/reference_audit.py')
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


class ReferencePortTests(unittest.TestCase):
    def copy_records(self, destination):
        for record in port.inventory()['generatedFrom'] + [{'path': 'references/checker.json'}]:
            target = destination / record['path']; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / record['path'], target)

    def first_source(self, root):
        name = 'provenance.json'
        entry = port.load(root, name)['copied'][0]
        return name, entry['local'], entry['sha256']

    def test_inventory_reads_every_declared_copy(self):
        declared = port.load(ROOT, 'provenance.json')
        rows = port.inventory()['references']
        actual = {f['local'] for r in rows for f in r['files'] if f['local']}
        self.assertTrue({f['local'] for f in declared['copied'] + declared['pinned']} <= actual)
        self.assertEqual(sum(len(r['files']) for r in rows if r.get('materialStatus') == 'historical'), len(declared['pinned']))
        self.assertTrue(any(r['id'].startswith('legacy-import:') for r in rows))

    def test_current_declaration_mutation_is_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.copy_records(root)
            name, local, old = self.first_source(root)
            text = (root / name).read_text()
            self.assertIn(old, text)
            (root / name).write_text(text.replace(old, '0' * 64, 1))
            rows = port.inventory(root)['references']
            actual = [f['sha256'] for row in rows for f in row['files'] if f['local'] == local]
            self.assertIn('0' * 64, actual)
            self.assertNotEqual(port.inventory()['generatedFrom'], port.inventory(root)['generatedFrom'])

    def test_unusable_digest_refuses_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.copy_records(root)
            name, _, old = self.first_source(root)
            (root / name).write_text((root / name).read_text().replace(old, 'not-a-digest', 1))
            with self.assertRaisesRegex(ValueError, 'unusable recorded digest'):
                port.inventory(root)

    def test_checker_digest_is_verified_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory); (source / 'scripts').mkdir()
            (source / 'scripts/check_references.py').write_text('raise RuntimeError("must never execute")')
            pin = json.loads((ROOT / 'references/checker.json').read_text())
            with patch.object(port.subprocess, 'check_output', return_value=pin['commit'] + '\n'):
                with self.assertRaisesRegex(ValueError, 'digest differs'):
                    port.verified_checker(ROOT, source)
            with patch.object(port.subprocess, 'check_output', return_value='f' * 40 + '\n'):
                with self.assertRaisesRegex(ValueError, 'HEAD differs'):
                    port.verified_checker(ROOT, source)

    def test_new_legacy_inventory_preserves_the_existing_header_payload_relation(self):
        import hashlib
        record = port.load(ROOT, 'references/classification.json')['legacyImports'][0]
        data = (ROOT / record['local']).read_bytes()
        header = record['adjustment']['header'].encode()
        self.assertTrue(data.startswith(header))
        self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'])
        self.assertEqual(hashlib.sha256(data[len(header):]).hexdigest(), record['upstreamSha256'])
        self.assertEqual(record['release'], 'v0.4.0')
