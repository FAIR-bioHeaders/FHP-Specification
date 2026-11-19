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
                with self.assertRaisesRegex(ValueError, 'differs|differ'):
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


class SourceAttributionTests(unittest.TestCase):
    copy_records = ReferencePortTests.copy_records

    def test_controlling_authority_fields_are_never_silently_substituted(self):
        mutations = [('provenance.json', ['source'], None), ('provenance.json', ['source', 'repository'], 'other/authority'), ('provenance.json', ['source', 'url'], 'https://example.invalid/authority'), ('provenance.json', ['source', 'ref'], 'main'), ('provenance.json', ['fhpContract', 'w3id'], 'https://example.invalid/fhp/v0.6.0'), ('tests/fixtures/fhp/v0.4.0/PROVENANCE.json', ['repository'], 'https://github.com/other/authority'), ('tests/fixtures/fhp/v0.4.0/PROVENANCE.json', ['files', 'fhp.json', 'source'], 'https://example.invalid/84c2f90ab0e97c81d8afbf33eafe80ebade7a009/fhp.json'), ('.github/schema-baseline-refs.json', ['authority', 'repository'], 'other/authority'), ('.github/schema-baseline-refs.json', ['authority', 'url'], 'https://example.invalid/authority'), ('.github/schema-baseline-refs.json', ['baselines', 0, 'authority', 'citation'], 'https://example.invalid/fhr/v0.3.1'), ('.github/schema-baseline-refs.json', ['baselines', 0, 'authority', 'pinnedSourceUrl'], 'https://example.invalid/v0.3.1/fhr.json'), ('references/classification.json', ['authority', 'repository'], 'other/authority'), ('references/classification.json', ['authority', 'url'], 'https://example.invalid/authority')]
        for filename, keys, replacement in mutations:
            for remove in (False, True):
                with self.subTest(filename=filename, keys=keys, remove=remove):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory); self.copy_records(root)
                        value = json.loads((root / filename).read_text())
                        target = value
                        for key in keys[:-1]:
                            target = target[key]
                        if remove:
                            del target[keys[-1]]
                        else:
                            target[keys[-1]] = replacement
                        (root / filename).write_text(json.dumps(value))
                        with self.assertRaises((ValueError, KeyError)):
                            port.inventory(root)

    def fixture(self, root):
        import hashlib
        import subprocess
        source, consumer = root / 'source', root / 'consumer'
        (source / 'scripts').mkdir(parents=True)
        consumer.mkdir(); self.copy_records(consumer)
        (consumer / 'scripts').mkdir(exist_ok=True)
        shutil.copyfile(ROOT / 'scripts/reference_audit.py', consumer / 'scripts/reference_audit.py')
        script = source / 'scripts/check_references.py'
        script.write_text('import json\nprint(json.dumps({"isolated": True}))\n')
        for command in (['git', 'init', '-q', str(source)], ['git', '-C', str(source), 'add', '.'],
                        ['git', '-C', str(source), '-c', 'user.name=Audit fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture']):
            subprocess.run(command, capture_output=True, check=True)
        commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        pin = dict(repository=port.AUTHORITY, path='scripts/check_references.py', commit=commit,
                   sha256=hashlib.sha256(script.read_bytes()).hexdigest())
        (consumer / 'references/checker.json').write_text(json.dumps(pin))
        return source, consumer, script, pin

    def test_joint_file_and_recorded_digest_tamper_fails_immutable_blob_binding(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            source, consumer, script, pin = self.fixture(Path(directory))
            self.assertEqual(port.verified_checker(consumer, source), script.resolve())
            script.write_text('raise RuntimeError("unreviewed code")\n')
            pin['sha256'] = hashlib.sha256(script.read_bytes()).hexdigest()
            (consumer / 'references/checker.json').write_text(json.dumps(pin))
            with self.assertRaisesRegex(ValueError, 'immutable commit'):
                port.verified_checker(consumer, source)

    def test_actual_runner_isolates_unverified_neighbor_module(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, consumer, script, _ = self.fixture(root)
            marker = root / 'shadow-executed'
            (source / 'scripts/json.py').write_text(
                'from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\nraise RuntimeError("shadow")\n')
            unisolated = subprocess.run([sys.executable, str(script)], capture_output=True)
            self.assertNotEqual(unisolated.returncode, 0)
            self.assertTrue(marker.exists())
            marker.unlink()
            actual = subprocess.run([sys.executable, str(consumer / 'scripts/reference_audit.py'),
                                     '--checker-root', str(source)], capture_output=True, text=True)
            self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
            self.assertEqual(json.loads(actual.stdout), {'isolated': True})
            self.assertFalse(marker.exists())

    def test_checker_metadata_and_symlink_sources_are_refused(self):
        for field, bad in [('repository', 'unexpected/authority'), ('commit', 'main'),
                           ('path', '../check_references.py'), ('sha256', 'not-a-digest'), ('url', 'https://example.invalid/source')]:
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    source, consumer, _, pin = self.fixture(Path(directory))
                    pin[field] = bad
                    (consumer / 'references/checker.json').write_text(json.dumps(pin))
                    with self.assertRaises(ValueError):
                        port.verified_checker(consumer, source)
        with tempfile.TemporaryDirectory() as directory:
            source, consumer, script, _ = self.fixture(Path(directory))
            script.rename(script.with_name('other.py'))
            script.symlink_to('other.py')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                port.verified_checker(consumer, source)


class ReaderAndVocabularyScopeTests(unittest.TestCase):
    copy_records = ReferencePortTests.copy_records

    def test_actual_reader_release_aliases_use_the_readers_local_copy(self):
        rows = {r['id']: r for r in port.inventory()['references']}
        self.assertEqual(rows['reader-release:v0.4.1']['files'][0]['local'], 'tests/fixtures/releases/fhp-v0.4.0.json')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.copy_records(root)
            path = root / 'tests/fhp_microdata.py'
            path.write_text(path.read_text().replace('"v0.4.1": "fhp-v0.4.0.json"', '"v0.4.1": "fhp-v0.5.0.json"'))
            altered = {r['id']: r for r in port.inventory(root)['references']}
            self.assertEqual(altered['reader-release:v0.4.1']['files'][0]['local'], 'tests/fixtures/releases/fhp-v0.5.0.json')
            self.assertNotEqual(altered['reader-release:v0.4.1']['files'][0]['sha256'], rows['reader-release:v0.4.1']['files'][0]['sha256'])

    def test_vocabulary_pin_is_read_from_current_source_and_bad_urls_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.copy_records(root)
            path = root / 'scripts/make_jsonld.py'
            original = path.read_text()
            digest = '0c641879818a1ce02ed10348b344cb11c37fd86c8a120a9f9bfe8e618d32042c'
            self.assertIn(digest, original)
            path.write_text(original.replace(digest, '0' * 64, 1))
            row = next(r for r in port.inventory(root)['references'] if r['id'] == 'vocabulary-source-pin')
            self.assertEqual(row['files'][0]['sha256'], '0' * 64)
            for content in [original.replace('FHP_SHARED_TERMS_URL = (', 'FHP_SHARED_TERMS_URL = ("https://example.invalid/" +', 1),
                            original.replace('FHP_SHARED_RELEASE_URL = (', 'FHP_SHARED_RELEASE_URL = ("https://example.invalid/" +', 1),
                            original.replace('FHP_SHARED_TERMS_URL = (', 'UNUSED_TERMS_URL = (', 1)]:
                path.write_text(content)
                with self.assertRaises(ValueError):
                    port.inventory(root)

    def test_reader_copy_locator_changes_require_explicit_adapter_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.copy_records(root)
            path = root / 'tests/fhp_microdata.py'
            original = path.read_text()
            changed = original.replace('parent / "fixtures" / "releases"', 'parent / "other-fixtures" / "releases"', 1)
            self.assertNotEqual(original, changed)
            path.write_text(changed)
            with self.assertRaises(ValueError):
                port.inventory(root)
