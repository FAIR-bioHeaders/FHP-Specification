#!/usr/bin/env python3
"""Check this repository's pinned shared-specification copies against provenance.json.

The files listed under ``copied`` in the root ``provenance.json`` are
byte-for-byte copies of the named paths at ``source.commit`` (or an entry's
own ``commit`` override) in FAIR-bioHeaders-Specification, following the
FHGFF3 ``header/provenance.json`` pattern adapted for this tree by issue #3.
Two copies carry a machine-checkable ``adjustment`` instead of plain identity
(``import-retarget`` replaces one import line; ``provenance-header`` prepends
an exact comment header) and record both the local and the upstream digest.

Without options this checks each copied file against the recorded digest, so it
needs only the standard library and works offline. With ``--upstream PATH`` it
also reads the pinned commits from a checkout of FAIR-bioHeaders-Specification,
re-applies every adjustment to the upstream bytes and compares for real, which
is what CI does. If an upstream checkout is found next to this repository (or
in ``FAIR_BIOHEADERS_SPECIFICATION``) the live comparison runs automatically;
``--no-upstream`` forces the digest-only check.

Every file under ``strictDirs`` must be classified: as a copied entry, under a
``legacy`` path or prefix (frozen pre-v0.5.0 family state, gated by the
DEVELOPMENT-TREE-PROPOSAL.md Q2 decision), or under ``owned`` (canonical in
this development repository). An unclassified new path fails the check.
Nothing here edits the copies; a deliberate resync re-runs
``scripts/make_provenance.py`` against the new pinned commit.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "provenance.json"
UPSTREAM_ENV = "FAIR_BIOHEADERS_SPECIFICATION"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_provenance():
    try:
        data = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"error: {PROVENANCE} is missing")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {PROVENANCE} is not valid JSON: {exc}")
    return data


def apply_adjustment(contents, adjustment):
    """The local bytes implied by an adjusted upstream copy; loud on mismatch."""
    kind = adjustment["kind"]
    if kind == "provenance-header":
        return adjustment["header"].encode("utf-8") + contents
    if kind == "import-retarget":
        old, new = adjustment["from"].encode("utf-8"), adjustment["to"].encode("utf-8")
        if contents.count(old) != 1:
            raise ValueError("import-retarget: upstream line not found exactly once")
        return contents.replace(old, new)
    raise ValueError(f"unknown adjustment kind {kind}")


def expected_local(upstream_bytes, entry):
    if "adjustment" in entry:
        return apply_adjustment(upstream_bytes, entry["adjustment"])
    return upstream_bytes


def check_local(prov):
    """Compare every copied file with its recorded (local) digest and size."""
    errors = []
    listed = {}
    for entry in prov.get("copied", []):
        local = entry["local"]
        listed[local] = entry
        path = ROOT / local
        if not path.is_file():
            errors.append(f"missing: {local}")
            continue
        data = path.read_bytes()
        if len(data) != entry["size"]:
            errors.append(f"size differs: {local} (local {len(data)}, "
                          f"pinned {entry['size']})")
        if sha256(data) != entry["sha256"]:
            errors.append(f"content differs: {local} (local {sha256(data)[:12]}..., "
                          f"pinned {entry['sha256'][:12]}...)")
    return errors, listed


def classified(prov):
    """Local paths classified as copied, legacy or owned (prefixes end in /)."""
    exact = {entry["local"] for entry in prov.get("copied", [])}
    prefixes = set()
    for group in ("legacy", "owned"):
        for item in prov.get(group, []):
            path = item["path"] if isinstance(item, dict) else item
            if path.endswith("/"):
                prefixes.add(path)
            else:
                exact.add(path)
    return exact, prefixes


def check_extras(prov, listed):
    """Fail on files present in a strict directory but not in provenance."""
    errors = []
    exact, prefixes = classified(prov)
    for rel_dir in prov.get("strictDirs", []):
        directory = ROOT / rel_dir
        if not directory.is_dir():
            errors.append(f"strictDir missing: {rel_dir}")
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in exact or rel in listed:
                continue
            if any(rel.startswith(prefix) for prefix in prefixes):
                continue
            errors.append(f"unclassified file under {rel_dir}: {rel}")
    return errors


def find_upstream(explicit):
    if explicit:
        path = Path(explicit).expanduser()
        if not (path / ".git").exists():
            sys.exit(f"error: --upstream {explicit} is not a git checkout")
        return path
    env = os.environ.get(UPSTREAM_ENV)
    if env:
        path = Path(env).expanduser()
        if (path / ".git").exists():
            return path
    for parent in ROOT.parents:  # worktree-aware: walks up to the workspace root
        candidate = parent / "FAIR-bioHeaders-Specification"
        if (candidate / ".git").exists():
            return candidate
    return None


def git_show(repo, commit, path):
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def check_upstream(prov, repo):
    """Compare the pinned commits' bytes with the recorded digests and copies."""
    errors = []
    default_commit = prov["source"]["commit"]
    for commit in dict.fromkeys(e.get("commit", default_commit)
                                for e in prov.get("copied", []) + prov.get("imports", [])):
        exists = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if exists.returncode != 0:
            errors.append(f"pinned commit {commit[:12]}... is not in {repo}")
    if errors:
        return errors, 0
    checked = 0
    for entry in prov.get("copied", []) + prov.get("imports", []):
        commit = entry.get("commit", default_commit)
        data = git_show(repo, commit, entry["upstream"])
        if data is None:
            errors.append(f"pinned commit {commit[:12]}... has no {entry['upstream']}")
            continue
        upstream_digest = entry.get("upstreamSha256", entry["sha256"])
        if sha256(data) != upstream_digest:
            errors.append(f"pinned {entry['upstream']} does not match its "
                          "recorded upstream digest")
        if "local" in entry:
            local = ROOT / entry["local"]
            want = expected_local(data, entry)
            if local.is_file() and local.read_bytes() != want:
                errors.append(f"local {entry['local']} differs from pinned "
                              f"{entry['upstream']} (adjustment re-applied)")
        checked += 1
    return errors, checked


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--upstream", metavar="PATH",
        help="FAIR-bioHeaders-Specification checkout to compare against")
    parser.add_argument(
        "--no-upstream", action="store_true",
        help="only check the recorded digests, even if a checkout is available")
    args = parser.parse_args(argv)

    prov = load_provenance()
    commit = prov["source"]["commit"]
    print(f"shared parity: pinned {prov['source']['repository']} {commit}")
    print(f"  {len(prov.get('copied', []))} copied files, "
          f"{len(prov.get('imports', []))} recorded imports")

    errors, listed = check_local(prov)
    errors += check_extras(prov, listed)

    upstream = None if args.no_upstream else find_upstream(args.upstream)
    if upstream is not None:
        upstream_errors, checked = check_upstream(prov, upstream)
        errors += upstream_errors
        print(f"  compared against pinned bytes in {upstream} ({checked} files)")
    elif args.upstream:
        sys.exit("error: --upstream was given but is not usable")
    else:
        print("  no upstream checkout found; checked recorded digests only")

    if errors:
        print("\nFAIL: a pinned shared copy has diverged:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("\nOK: every pinned shared copy matches provenance.json"
          + (" and the pinned commits." if upstream is not None else
             " (digest-only; pass --upstream for the byte comparison)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
