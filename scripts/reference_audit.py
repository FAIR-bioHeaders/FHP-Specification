#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Audit CURRENT owning declarations with one immutable shared checker; never repin."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = 'FAIR-bioHeaders/FAIR-bioHeaders-Specification'
CONSUMER = 'FAIR-bioHeaders/FHP-Specification'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(root, name):
    data = json.loads((root / name).read_text())
    if not isinstance(data, dict):
        raise ValueError(name + ': expected object')
    return data


def measured_file(local, upstream, sha, **extra):
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
        raise ValueError(str(local or upstream) + ': unusable recorded digest')
    return dict(local=local, path=upstream, sha256=sha, **extra)


def reference(identity, cls, revision, files, commit=None, **extra):
    if not isinstance(revision, str) or not revision:
        raise ValueError(identity + ': unusable recorded revision')
    if commit is not None and (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)):
        raise ValueError(identity + ': unusable recorded commit')
    row = dict(id=identity, consumer=CONSUMER, repository=AUTHORITY, **{'class': cls},
               revision=revision, revisionKind='tag' if revision.startswith('v') else 'commit', files=files)
    if commit:
        row['commit'] = commit
    row.update(extra)
    return row


def literal_assignments(root, name, wanted):
    found = {}
    for node in ast.parse((root / name).read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    found[target.id] = ast.literal_eval(node.value)
    if set(found) != set(wanted):
        raise ValueError(name + ': missing declared constants')
    return found


def declarations(root):
    name = 'provenance.json'; data = load(root, name); source = data['source']
    if source.get('ref') != source['tag']:
        raise ValueError('Released provenance source.ref must equal source.tag')
    classification = load(root, 'references/classification.json')
    groups = {}
    for entry in data['copied']:
        commit = entry.get('commit', source['commit'])
        release = source['tag'] if commit == source['commit'] else classification['releaseOverrides'].get(commit)
        if not release:
            raise ValueError('Unclassified released-copy override: ' + commit)
        extra = {k: entry[k] for k in ('upstreamSha256', 'adjustment') if k in entry}
        groups.setdefault((release, commit), []).append(measured_file(entry['local'], entry['upstream'], entry['sha256'], **extra))
    rows = []
    for (release, commit), files in groups.items():
        patterns = sorted({f['path'] for f in files})
        if commit == source['commit']:
            patterns += ['conformance/valid/fhp-fasta-*', 'conformance/invalid/fhp-fasta-*']
        rows.append(reference('copied:' + release, 'copied-tree', release, files, commit,
                              materialStatus='released', sourcePatterns=patterns))
    historical = {}
    for entry in data['pinned']:
        historical.setdefault(entry['commit'], []).append(measured_file(entry['local'], entry['upstream'], entry['sha256']))
    for commit, files in historical.items():
        rows.append(reference('historical:' + commit, 'copied-tree', commit, files, commit, materialStatus='historical'))
    for entry in data['imports']:
        suite = entry['upstream'] == 'conformance/manifest.json'
        rows.append(reference('import:' + entry['upstream'], 'conformance-suite' if suite else 'released-contract',
                              source['commit'] if suite else source['tag'],
                              [measured_file(None, entry['upstream'], entry['sha256'])], source['commit']))
    fixture_name = 'tests/fixtures/fhp/v0.4.0/PROVENANCE.json'; fixture = load(root, fixture_name)
    for local, entry in fixture['files'].items():
        upstream = entry['source'].split('/' + fixture['release_commit'] + '/', 1)[1]
        rows.append(reference('v04-fixture:' + local, 'released-contract', fixture['release'],
                              [measured_file('tests/fixtures/fhp/v0.4.0/' + local, upstream, entry['sha256'])], fixture['release_commit']))
    baseline_name = '.github/schema-baseline-refs.json'; baseline = load(root, baseline_name)
    for tag, entry in baseline['fhrReleaseLine']['tags'].items():
        rows.append(reference('fhr-release-evidence:' + tag, 'released-contract', tag,
                              [measured_file(None, entry['path'], entry['sha256'])], entry['commit']))
    for entry in baseline['baselines']:
        if 'authority' in entry:
            authority = entry['authority']
            rows.append(reference('baseline-reviewed-schema:' + entry['local'], 'released-contract', authority['ref'],
                                  [measured_file(entry['reviewedSchema']['local'], authority['path'], authority['sha256'])], authority['commit']))
    for entry in classification['legacyImports']:
        rows.append(reference('legacy-import:' + entry['local'], 'copied-tree', entry['release'],
                              [measured_file(entry['local'], entry['upstream'], entry['sha256'],
                                             upstreamSha256=entry['upstreamSha256'], adjustment=entry['adjustment'])],
                              entry['commit'], materialStatus='released'))
    return rows, [name, fixture_name, baseline_name, 'references/classification.json'], [
        f"All{len(data['copied'])} copied,{len(data['pinned'])} historical pinned and{len(data['imports'])} import entries are read from current provenance, including declared adjustments/overrides.",
        'The complete release-owned FHP vector scope is compared against its tag. The local conformance tree also contains intentionally historical/owned material; existing check_shared_parity.py guards local classification and transformations.',
        'The legacy core-v0.4 snapshot is measured against its already-stated release payload, with its unchanged exact comment header separately pinned.',
        'Review-baseline authority claims are audited as source references, not byte-copy claims for canonicalized/retargeted baseline JSON; local baseline semantic guards remain required.',
        'Dated liveMain/sweep notes are historical observations, not runtime retrieval pins. Same-repository source, adapted test implementation, package/action/tool dependencies and biological provenance are outside the five contract reference classes.']



def inventory(root=ROOT):
    rows, records, notes = declarations(root)
    if not rows:
        raise ValueError('No references declared')
    return dict(inventoryVersion=1, advisory=True, references=rows,
                generatedFrom=[dict(path=name, sha256=digest((root / name).read_bytes())) for name in records],
                coverageNotes=notes,
                coverageGaps=['Other consumer repositories require their own rollout; this port alone does not close shared #241.'])


def verified_checker(root, source):
    pin = load(root, 'references/checker.json')
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != pin['commit']:
        raise ValueError('Checker checkout HEAD differs from the reviewed source pin')
    script = (source / pin['path']).resolve()
    if not script.is_relative_to(source.resolve()):
        raise ValueError('Checker path escapes the reviewed source checkout')
    if digest(script.read_bytes()) != pin['sha256']:
        raise ValueError('Checker source digest differs; refusing execution')
    return script


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checker-root', type=Path)
    parser.add_argument('--inventory-only', action='store_true')
    parser.add_argument('--inventory-output', type=Path)
    parser.add_argument('--checkout', action='append', default=[], metavar='OWNER/REPO=PATH')
    parser.add_argument('--strict', action='store_true', help='exit nonzero on findings (advisory by default)')
    args = parser.parse_args(argv)
    try:
        table = inventory()
        if args.inventory_output:
            args.inventory_output.write_text(json.dumps(table, indent=2) + '\n')
        if args.inventory_only:
            print(json.dumps(table, indent=2))
            return 0
        if not args.checker_root:
            parser.error('--checker-root is required for execution')
        script = verified_checker(ROOT, args.checker_root)
        with tempfile.TemporaryDirectory() as directory:
            table_file = Path(directory) / 'inventory.json'
            table_file.write_text(json.dumps(table))
            command = [sys.executable, str(script), '--inventory', str(table_file),
                       '--consumer', CONSUMER, '--consumer-root', str(ROOT)]
            for mapping in args.checkout:
                command += ['--checkout', mapping]
            if args.strict:
                command.append('--exit-on-findings')
            return subprocess.run(command, check=False).returncode
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(json.dumps(dict(advisory=True, status='UNUSABLE', error=str(error), wrotePins=[])))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
