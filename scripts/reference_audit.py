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
    if sha not in (None, '') and (not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha)):
        raise ValueError(str(local or upstream) + ': unusable recorded digest')
    return dict(local=local, path=upstream, sha256=sha, **extra)


def reference(identity, cls, revision, files, commit=None, **extra):
    if revision not in (None, '') and not isinstance(revision, str):
        raise ValueError(identity + ': unusable recorded revision')
    if commit not in (None, '') and (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)):
        raise ValueError(identity + ': unusable recorded commit')
    row = dict(id=identity, consumer=CONSUMER, repository=AUTHORITY, **{'class': cls},
               revision=revision, revisionKind='tag' if not revision or revision.startswith('v') else 'commit' if re.fullmatch('[0-9a-f]{40}', revision) else 'branch', files=files)
    if commit:
        row['commit'] = commit
    row.update(extra)
    return row


def validated_bindings(root, filename, wanted):
    """Accept each consumed binding/dependency once, as a top-level assignment."""
    tree = ast.parse((root / filename).read_text())
    assignments = {}
    candidates = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            candidates.setdefault(statement.targets[0].id, []).append(statement)
    needed = set(wanted)
    pending = list(wanted)
    while pending:
        name = pending.pop()
        for statement in candidates.get(name, []):
            for node in ast.walk(statement.value):
                if isinstance(node, ast.Name) and node.id not in needed:
                    needed.add(node.id)
                    pending.append(node.id)
    for name in needed:
        entries = candidates.get(name, [])
        if len(entries) > 1:
            raise ValueError(filename + ': reassigned source binding ' + name)
        if entries:
            assignments[name] = entries[0].value
    permitted = {id(entries[0].targets[0]) for name, entries in candidates.items() if name in needed and len(entries) == 1}
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id in needed and id(node) not in permitted:
                raise ValueError(filename + ': unsupported source binding write ' + node.id)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                base = node.func.value
                if isinstance(base, ast.Name) and base.id in needed:
                    raise ValueError(filename + ': unsupported source binding mutation ' + base.id)
            if isinstance(node, (ast.Subscript, ast.Attribute)) and isinstance(node.ctx, (ast.Store, ast.Del)):
                if any(isinstance(part, ast.Name) and part.id in needed for part in ast.walk(node)):
                    raise ValueError(filename + ': unsupported source binding mutation')
    return assignments


def literal_assignments(root, name, wanted):
    found = {key: ast.literal_eval(value) for key, value in validated_bindings(root, name, wanted).items() if key in wanted}
    if set(found) != set(wanted):
        raise ValueError(name + ': missing declared constants')
    return found


def require_authority(data, context):
    if isinstance(data, dict) and any(k in data for k in ('source', 'authority', 'source_repository', 'sourceUrl')):
        raise ValueError(context + ': unsupported nested source override')
    if not isinstance(data, dict) or data.get('repository') != AUTHORITY:
        raise ValueError(context + ': missing or unexpected source repository')
    if data.get('url') != 'https://github.com/' + AUTHORITY:
        raise ValueError(context + ': missing or unexpected source URL')


def reject_source_overrides(entry, context):
    for key in ('repository', 'url', 'source', 'authority', 'source_repository', 'sourceUrl'):
        if key in entry:
            raise ValueError(context + ': unsupported per-entry source override ' + key)


def string_declarations(root, filename, wanted):
    assignments = validated_bindings(root, filename, wanted)
    active = set()
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in assignments and node.id not in active:
            active.add(node.id)
            try:
                return evaluate(assignments[node.id])
            finally:
                active.remove(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return evaluate(node.left) + evaluate(node.right)
        if isinstance(node, ast.JoinedStr):
            result = ''
            for item in node.values:
                if isinstance(item, ast.FormattedValue):
                    if item.conversion != -1 or item.format_spec is not None:
                        raise ValueError(filename + ': unsupported string conversion')
                    result += evaluate(item.value)
                else:
                    result += evaluate(item)
            return result
        raise ValueError(filename + ': unsupported source declaration expression')
    if not set(wanted) <= set(assignments):
        raise ValueError(filename + ': missing source declarations')
    return {name: evaluate(assignments[name]) for name in wanted}


def require_assignment(root, filename, name, expression):
    expected = ast.dump(ast.parse(expression, mode='eval').body)
    for node in ast.parse((root / filename).read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            if ast.dump(node.value) == expected:
                return
            break
    raise ValueError(filename + ': missing or unsupported ' + name + ' locator')


def declarations(root):
    name = 'provenance.json'; data = load(root, name); source = data['source']
    require_authority(source, 'provenance source')
    if source.get('ref') and source.get('tag') and source['ref'] != source['tag']:
        raise ValueError('Released provenance source.ref must equal source.tag')
    source_release = source.get('ref') if source.get('tag') and source.get('ref') else None
    classification = load(root, 'references/classification.json')
    require_authority(classification.get('authority'), 'classification authority')
    for entry in data['copied'] + data['pinned'] + data['imports'] + classification['legacyImports']:
        reject_source_overrides(entry, 'provenance entry')
    contract = data['fhpContract']
    if contract['w3id'] != 'https://w3id.org/fair-bioheaders/fhp/' + contract['sharedRelease']:
        raise ValueError('Unexpected FHP contract citation authority')
    groups = {}
    for entry in data['copied']:
        commit = entry.get('commit', source.get('commit'))
        release = source_release if commit == source.get('commit') else classification['releaseOverrides'].get(commit)
        if not release and commit != source.get('commit'):
            raise ValueError('Unclassified released-copy override: ' + str(commit))
        extra = {k: entry[k] for k in ('upstreamSha256', 'adjustment') if k in entry}
        groups.setdefault((release, commit), []).append(measured_file(entry['local'], entry.get('upstream'), entry.get('sha256'), **extra))
    rows = []
    for (release, commit), files in groups.items():
        patterns = sorted({f['path'] for f in files if f['path']})
        if commit == source.get('commit'):
            patterns += ['conformance/valid/fhp-fasta-*', 'conformance/invalid/fhp-fasta-*']
        rows.append(reference('copied:' + str(release), 'copied-tree', release, files, commit,
                              materialStatus='released', sourcePatterns=patterns))
    historical = {}
    for entry in data['pinned']:
        historical.setdefault(entry.get('commit'), []).append(measured_file(entry['local'], entry.get('upstream'), entry.get('sha256')))
    for commit, files in historical.items():
        rows.append(reference('historical:' + str(commit), 'copied-tree', commit, files, commit, materialStatus='historical'))
    for entry in data['imports']:
        suite = entry.get('upstream') == 'conformance/manifest.json'
        rows.append(reference('import:' + str(entry.get('upstream')), 'conformance-suite' if suite else 'released-contract',
                              source.get('commit') if suite else source_release,
                              [measured_file(None, entry.get('upstream'), entry.get('sha256'))], source.get('commit')))
    fixture_name = 'tests/fixtures/fhp/v0.4.0/PROVENANCE.json'; fixture = load(root, fixture_name)
    if fixture.get('repository') != 'https://github.com/' + AUTHORITY:
        raise ValueError('Missing or unexpected fixture source repository')
    for local, entry in fixture['files'].items():
        if any(k in entry for k in ('repository', 'url', 'authority', 'source_repository', 'sourceUrl')):
            raise ValueError('Unsupported fixture source attribution override')
        url = entry.get('source')
        upstream = None
        if url:
            prefix = 'https://raw.githubusercontent.com/' + AUTHORITY + '/'
            if not isinstance(url, str) or not url.startswith(prefix) or '/' not in url[len(prefix):]:
                raise ValueError('Unexpected fixture source URL')
            url_commit, upstream = url[len(prefix):].split('/', 1)
            if fixture.get('release_commit') and url_commit != fixture['release_commit']:
                raise ValueError('Fixture source URL disagrees with recorded commit')
            if not upstream or '..' in Path(upstream).parts:
                raise ValueError('Unusable fixture source path')
        rows.append(reference('v04-fixture:' + local, 'released-contract', fixture.get('release'),
                              [measured_file('tests/fixtures/fhp/v0.4.0/' + local, upstream, entry.get('sha256'))], fixture.get('release_commit')))
    baseline_name = '.github/schema-baseline-refs.json'; baseline = load(root, baseline_name)
    require_authority(baseline.get('authority'), 'baseline authority')
    for tag, entry in baseline['fhrReleaseLine']['tags'].items():
        reject_source_overrides(entry, 'release evidence')
        rows.append(reference('fhr-release-evidence:' + tag, 'released-contract', tag,
                              [measured_file(None, entry.get('path'), entry.get('sha256'))], entry.get('commit')))
    for entry in baseline['baselines']:
        if 'authority' in entry:
            authority = entry['authority']
            reject_source_overrides(authority, 'baseline per-artifact authority')
            citation, source_url = authority.get('citation'), authority.get('pinnedSourceUrl')
            if not isinstance(citation, str) or not citation.startswith('https://w3id.org/fair-bioheaders/') or not isinstance(source_url, str) or not source_url.startswith('https://raw.githubusercontent.com/' + AUTHORITY + '/'):
                raise ValueError('Missing or unexpected baseline citation/source URL')
            if authority.get('path') and authority.get('ref') and (citation != 'https://w3id.org/fair-bioheaders/' + Path(authority['path']).stem + '/' + authority['ref'] or source_url != 'https://raw.githubusercontent.com/' + AUTHORITY + '/' + authority['ref'] + '/' + authority['path']):
                raise ValueError('Baseline citation/source URL disagrees with recorded path/ref')
            rows.append(reference('baseline-reviewed-schema:' + entry['local'], 'released-contract', authority.get('ref'),
                                  [measured_file(entry['reviewedSchema']['local'], authority.get('path'), authority.get('sha256'))], authority.get('commit')))
    for entry in classification['legacyImports']:
        rows.append(reference('legacy-import:' + entry['local'], 'copied-tree', entry.get('release'),
                              [measured_file(entry['local'], entry.get('upstream'), entry.get('sha256'),
                                             upstreamSha256=entry['upstreamSha256'], adjustment=entry['adjustment'])],
                              entry.get('commit'), materialStatus='released'))
    reader_name = 'tests/fhp_microdata.py'
    aliases = literal_assignments(root, reader_name, {'SUPPORTED_RELEASES'})['SUPPORTED_RELEASES']
    require_assignment(root, reader_name, 'RELEASES_DIR', "Path(__file__).resolve().parent / 'fixtures' / 'releases'")
    if not isinstance(aliases, dict) or not aliases:
        raise ValueError('Missing supported-release aliases')
    by_local = {e['local']: e for e in data['copied'] + data['pinned']}
    for tag, filename in aliases.items():
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError('Unusable supported-release local filename')
        local = 'tests/fixtures/releases/' + filename
        if tag not in baseline['fhrReleaseLine']['tags']:
            raise ValueError('Supported release has no declared tag/commit authority')
        if local == 'tests/fixtures/releases/fhp-v0.4.0.json':
            sha = fixture['files']['fhp.json'].get('sha256')
        elif local in by_local:
            sha = by_local[local].get('sha256')
        else:
            raise ValueError('Supported reader copy has no recorded digest')
        rows.append(reference('reader-release:' + tag, 'released-contract', tag,
                              [measured_file(local, 'fhp.json', sha)],
                              baseline['fhrReleaseLine']['tags'][tag].get('commit')))
    vocabulary_name = 'scripts/make_jsonld.py'
    vocab = string_declarations(root, vocabulary_name, {
        'FHP_SHARED_RELEASE', 'FHP_SHARED_COMMIT', 'FHP_SHARED_TERMS_SHA256',
        'FHP_SHARED_TERMS_URL', 'FHP_SHARED_RELEASE_URL'})
    if vocab['FHP_SHARED_TERMS_URL'] != 'https://raw.githubusercontent.com/' + AUTHORITY + '/' + vocab['FHP_SHARED_COMMIT'] + '/jsonld/terms.ttl' or vocab['FHP_SHARED_RELEASE_URL'] != 'https://github.com/' + AUTHORITY + '/releases/tag/' + vocab['FHP_SHARED_RELEASE']:
        raise ValueError('Missing or unexpected declared vocabulary source URL')
    rows.append(reference('fhp-jsonld-shared-terms', 'released-contract', vocab['FHP_SHARED_RELEASE'],
                          [measured_file(None, 'jsonld/terms.ttl', vocab['FHP_SHARED_TERMS_SHA256'])],
                          vocab['FHP_SHARED_COMMIT']))
    return rows, [name, fixture_name, baseline_name, 'references/classification.json', reader_name, vocabulary_name], [
        f"All {len(data['copied'])} copied, {len(data['pinned'])} historical pinned and {len(data['imports'])} import entries are read from current provenance, including declared adjustments/overrides.",
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
    if any(k in pin for k in ('url', 'source', 'authority', 'source_repository', 'sourceUrl')):
        raise ValueError('Unsupported checker source attribution override')
    if pin.get('repository') != AUTHORITY or pin.get('path') != 'scripts/check_references.py':
        raise ValueError('Missing or unexpected checker source repository/path')
    if not isinstance(pin.get('commit'), str) or not re.fullmatch('[0-9a-f]{40}', pin['commit']):
        raise ValueError('Unusable immutable checker commit')
    if not isinstance(pin.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', pin['sha256']):
        raise ValueError('Unusable checker digest')
    if source.is_symlink() or (source / 'scripts').is_symlink() or (source / pin['path']).is_symlink():
        raise ValueError('Checker source path must not be a symlink')
    script = (source / pin['path']).resolve()
    if not script.is_relative_to(source.resolve()):
        raise ValueError('Checker path escapes the reviewed source checkout')
    actual = subprocess.check_output(['git', '--no-replace-objects', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != pin['commit']:
        raise ValueError('Checker checkout HEAD differs from the reviewed source pin')
    immutable = subprocess.check_output(['git', '--no-replace-objects', '-C', str(source), 'show', pin['commit'] + ':' + pin['path']])
    if script.read_bytes() != immutable:
        raise ValueError('Checker working bytes differ from the immutable commit')
    if digest(immutable) != pin['sha256']:
        raise ValueError('Checker source digest differs; refusing execution')
    return immutable


def checker_snapshot(root, source, directory):
    immutable = verified_checker(root, source)
    script = Path(directory) / 'verified-checker.py'
    script.write_bytes(immutable)
    script.chmod(0o400)
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
        with tempfile.TemporaryDirectory() as directory:
            script = checker_snapshot(ROOT, args.checker_root, directory)
            table_file = Path(directory) / 'inventory.json'
            table_file.write_text(json.dumps(table))
            command = [sys.executable, '-I', str(script), '--inventory', str(table_file),
                       '--consumer', CONSUMER, '--consumer-root', str(ROOT)]
            for mapping in args.checkout:
                command += ['--checkout', mapping]
            if args.strict:
                command.append('--exit-on-findings')
            return subprocess.run(command, check=False).returncode
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError, subprocess.CalledProcessError) as error:
        print(json.dumps(dict(advisory=True, status='UNUSABLE', error=str(error), wrotePins=[])))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
