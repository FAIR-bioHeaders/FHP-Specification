#!/usr/bin/env python3
"""Required actual-engine controls use only a temporary synthetic git authority."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from reference_audit import ROOT, CONSUMER, checker_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checker-root', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        script = checker_snapshot(ROOT, args.checker_root, directory)
        authority = Path(directory) / 'authority'
        authority.mkdir()
        original = b'{"synthetic_reference_audit_control":true}\n'
        (authority / 'fixture.json').write_bytes(original)
        def git(*values):
            return subprocess.check_output(['git', '-C', str(authority), *values], stderr=subprocess.DEVNULL)
        git('init', '-q')
        git('add', '.')
        git('-c', 'commit.gpgsign=false', '-c', 'user.name=Advisory fixture',
            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        git('tag', 'v0.0.0-fixture')
        row = dict(id='unchanged', consumer=CONSUMER, repository='example/authority',
            revision='v0.0.0-fixture', revisionKind='tag', commit=git('rev-parse', 'HEAD').decode().strip(),
            files=[dict(path='fixture.json', sha256=hashlib.sha256(original).hexdigest())],
            **{'class': 'base-carrier'})
        wrong, absent, failed = (copy.deepcopy(row) for _ in range(3))
        wrong['id'] = 'wrong-digest'
        wrong['files'][0]['sha256'] = hashlib.sha256(original + b'actual controlled mutation').hexdigest()
        absent['id'] = 'absent'
        absent['files'][0]['path'] = 'missing.json'
        failed['id'] = 'unmapped-query'
        failed['repository'] = 'example/unmapped'
        incomplete = []
        for field in ('commit', 'revision', 'path', 'sha256'):
            missing = copy.deepcopy(row)
            missing['id'] = 'missing-' + field
            if field in ('commit', 'revision'):
                missing.pop(field)
            else:
                missing['files'][0].pop(field)
            incomplete.append(missing)
        floating = copy.deepcopy(row)
        floating.update(id='floating', revision='main', revisionKind='branch')
        copied = copy.deepcopy(row)
        copied.update(id='missing-copied-file', materialStatus='released',
                      sourcePatterns=['missing.json'], localTree='copied')
        copied['class'] = 'copied-tree'
        copied['files'][0].update(path='missing.json', local='copied/missing.json')
        source = Path(directory) / 'control.json'
        source.write_text(json.dumps(dict(inventoryVersion=1, references=[row, wrong, absent, failed, floating, copied, *incomplete])))
        result = subprocess.run([sys.executable, '-I', str(script), '--inventory', str(source),
            '--consumer', CONSUMER, '--consumer-root', str(authority), '--checkout',
            'example/authority=' + str(authority), '--exit-on-findings'], capture_output=True, text=True)
        report = json.loads(result.stdout)
        actual = {entry['id']: entry['verdict'] for entry in report['references']}
        wanted = {'unchanged': 'FRESH', 'wrong-digest': 'DRIFT', 'absent': 'ABSENT', 'unmapped-query': 'QUERY_FAILED'}
        wanted.update({entry['id']: 'ABSENT' for entry in incomplete})
        wanted.update({'floating': 'DRIFT', 'missing-copied-file': 'ABSENT'})
        if result.returncode != 1 or actual != wanted:
            raise RuntimeError('Synthetic actual-engine controls disagreed: ' + str(actual))
        if (authority / 'fixture.json').read_bytes() != original:
            raise RuntimeError('Control modified authority bytes')
    print(json.dumps(dict(wrotePins=[], controls=actual, report=report), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
