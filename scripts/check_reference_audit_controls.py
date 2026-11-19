#!/usr/bin/env python3
"""Actual accepted-engine controls on one current reference; no network or pin writes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from reference_audit import ROOT, AUTHORITY, CONSUMER, inventory, verified_checker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checker-root', type=Path, required=True)
    args = parser.parse_args()
    script = verified_checker(ROOT, args.checker_root)
    table = inventory()
    chosen = next((row, item) for row in table['references'] for item in row['files']
                  if item.get('local') and not item.get('upstreamSha256'))
    row, item = copy.deepcopy(chosen)
    row['files'] = [item]
    for key in ('sourcePatterns', 'localTree', 'localExclusions'):
        row.pop(key, None)
    original = (ROOT / item['local']).read_bytes()
    changed = original + b'\ncontrolled wrong digest; never written to source\n'
    if not original or original == changed:
        raise RuntimeError('Mutation has no actual bytes')
    outputs = {}
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / 'control.json'
        def run(label, control_row, mapping):
            source.write_text(json.dumps(dict(inventoryVersion=1, references=[control_row])))
            result = subprocess.run([sys.executable, '-I', str(script), '--inventory', str(source),
                '--consumer', CONSUMER, '--consumer-root', str(ROOT), '--checkout', mapping,
                '--exit-on-findings'], capture_output=True, text=True)
            report = json.loads(result.stdout)
            outputs[label] = dict(exit=result.returncode, report=report)
            return result.returncode, report['references'][0]['verdict']
        mapped = AUTHORITY + '=' + str(args.checker_root)
        if run('unchanged', row, mapped) != (0, 'FRESH'):
            raise RuntimeError('Actual unchanged reference is not FRESH')
        wrong = copy.deepcopy(row)
        wrong['files'][0]['sha256'] = hashlib.sha256(changed).hexdigest()
        if wrong['files'][0]['sha256'] == hashlib.sha256(original).hexdigest():
            raise RuntimeError('Wrong digest mutation did not change the measurement')
        if run('wrong-digest', wrong, mapped) != (1, 'DRIFT'):
            raise RuntimeError('Actual wrong recorded digest was not DRIFT')
        if run('unmapped-query', row, 'unrelated/repository=' + str(args.checker_root)) != (1, 'QUERY_FAILED'):
            raise RuntimeError('Failed query was confused with a confirmed absence or pass')
    print(json.dumps(dict(controlledReference=row['id'], wrotePins=[], controls=outputs), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
