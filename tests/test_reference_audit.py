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
        table = port.inventory()
        for record in table['generatedFrom'] + [{'path': 'references/checker.json'}]:
            target = destination / record['path']; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / record['path'], target)
        for row in table['references']:
            if row['id'].startswith(('reader-release:', 'fhp-jsonld-shared-terms')):
                for item in row['files']:
                    if item['local']:
                        target = destination / item['local']; target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(ROOT / item['local'], target)

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

    def test_reader_release_aliases_are_normalized_to_their_local_fixtures(self):
        declarations = port.literal_assignments(
            ROOT, 'tests/fhp_microdata.py', {'SUPPORTED_RELEASES'})['SUPPORTED_RELEASES']
        table = port.inventory()
        rows = {row['id']: row for row in table['references']
                if row['id'].startswith('reader-release:')}
        self.assertEqual(set(rows), {'reader-release:' + tag for tag in declarations})
        for tag, filename in declarations.items():
            row = rows['reader-release:' + tag]
            self.assertEqual(row['revision'], tag)
            self.assertEqual(row['files'][0]['path'], 'fhp.json')
            self.assertEqual(row['files'][0]['local'], 'tests/fixtures/releases/' + filename)
            self.assertEqual(row['files'][0]['sha256'],
                             port.digest((ROOT / row['files'][0]['local']).read_bytes()))
        generated = {record['path'] for record in table['generatedFrom']}
        self.assertIn('tests/fhp_microdata.py', generated)
        self.assertIn('scripts/make_jsonld.py', generated)

    def test_reader_release_mapping_mutation_is_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.copy_records(root)
            name = 'tests/fhp_microdata.py'
            source = root / name
            source.write_text(source.read_text().replace(
                '"v0.4.2": "fhp-v0.4.0.json"',
                '"v0.4.2": "fhp-v0.5.0.json"', 1))
            table = port.inventory(root)
            row = next(row for row in table['references'] if row['id'] == 'reader-release:v0.4.2')
            self.assertEqual(row['files'][0]['local'], 'tests/fixtures/releases/fhp-v0.5.0.json')
            self.assertNotEqual(port.inventory()['generatedFrom'], table['generatedFrom'])

    def test_jsonld_vocabulary_pin_mutations_are_observed(self):
        mutations = (
            ('FHP_SHARED_RELEASE = "v0.4.0"', 'FHP_SHARED_RELEASE = "v0.4.1"',
             'revision', 'v0.4.1'),
            ('FHP_SHARED_COMMIT = "84c2f90ab0e97c81d8afbf33eafe80ebade7a009"',
             'FHP_SHARED_COMMIT = "' + 'f' * 40 + '"', 'commit', 'f' * 40),
            ('"0c641879818a1ce02ed10348b344cb11c37fd86c8a120a9f9bfe8e618d32042c"',
             '"' + '0' * 64 + '"', 'sha256', '0' * 64),
        )
        for old, new, field, expected in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); self.copy_records(root)
                name = 'scripts/make_jsonld.py'
                source = root / name
                text = source.read_text()
                self.assertIn(old, text)
                source.write_text(text.replace(old, new, 1))
                table = port.inventory(root)
                row = next(row for row in table['references']
                           if row['id'] == 'fhp-jsonld-shared-terms')
                actual = row['files'][0]['sha256'] if field == 'sha256' else row[field]
                self.assertEqual(actual, expected)
                self.assertNotEqual(port.inventory()['generatedFrom'], table['generatedFrom'])

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
