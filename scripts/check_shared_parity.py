#!/usr/bin/env python3
"""Check this repository's pinned shared-specification copies against provenance.json.

The files listed under ``copied`` in the root ``provenance.json`` are
byte-for-byte copies of the named paths at ``source.commit`` (or an entry's
own ``commit`` override) in FAIR-bioHeaders-Specification, following the
FHGFF3 ``header/provenance.json`` pattern adapted for this tree by issue #3.
Two copies carry a machine-checkable ``adjustment`` instead of plain identity
(``import-retarget`` replaces named import lines, one occurrence each;
``provenance-header`` prepends an exact comment header) and record both the
local and the upstream digest.

Without options this checks each copied file against the recorded digest, so it
needs only the standard library and works offline. With ``--upstream PATH`` it
also reads the pinned commits from a checkout of FAIR-bioHeaders-Specification,
re-applies every adjustment to the upstream bytes and compares for real, which
is what CI does. If an upstream checkout is found next to this repository (or
in ``FAIR_BIOHEADERS_SPECIFICATION``) the live comparison runs automatically;
``--no-upstream`` forces the digest-only check.

The ``pinned`` section serves the Q2 freeze (docs/DEVELOPMENT-TREE.md,
FAIR-bioHeaders/FHP-Specification#2, 2026-11-12): the inherited FHR/FHGFF3
contracts, models and their generated outputs are pinned compatibility
fixtures, no longer generation or drift-check targets of this repository's CI.
Each entry records the local digest and the historical shared commit whose
bytes it froze (the fork state, one commit before shared v0.4.0); the same
digest and, with ``--upstream``, the recorded commit's bytes are verified, so
silent drift of a frozen artifact fails CI exactly like drift of a copied one.

Every file under ``strictDirs`` must be classified: as a copied entry, as a
pinned compatibility artifact, under a ``legacy`` path or prefix (frozen
pre-v0.5.0 family state), or under ``owned`` (canonical in this development
repository). An unclassified new path fails the check.
Nothing here edits the copies; a deliberate resync re-runs
``scripts/make_provenance.py`` against the new pinned commit.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
        validate_provenance(data)
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit(f"error: cannot read valid provenance from {PROVENANCE}: {exc}")
    return data


def adjustment_parts(adjustment):
    """Validate the adjustment grammar before applying any replacement."""
    if not isinstance(adjustment, dict):
        raise ValueError("adjustment must be an object")
    kind = adjustment.get("kind")
    if kind == "provenance-header":
        if not isinstance(adjustment.get("header"), str):
            raise ValueError("provenance-header requires a string header")
        return kind, adjustment["header"], None
    if kind == "import-retarget":
        olds, news = adjustment.get("from"), adjustment.get("to")
        if isinstance(olds, str) and isinstance(news, str):
            olds, news = [olds], [news]
        if (not isinstance(olds, list) or not isinstance(news, list)
                or not olds or len(olds) != len(news)
                or any(not isinstance(item, str) or not item for item in olds)
                or any(not isinstance(item, str) for item in news)):
            raise ValueError("import-retarget requires equally sized nonempty string pairs")
        return kind, olds, news
    raise ValueError(f"unknown adjustment kind {kind}")


def validate_provenance(prov):
    """Reject malformed declarations before indexing fields or reading paths."""
    def text(value, label):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a nonempty string")

    def path(value, label, prefix=False):
        text(value, label)
        clean = value[:-1] if prefix and value.endswith("/") else value
        if ("\\" in clean or "\0" in clean
                or any(part in {"", ".", ".."} for part in clean.split("/"))):
            raise ValueError(f"{label} must be a repository-relative path")

    def hexadecimal(value, length, label):
        if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", value):
            raise ValueError(f"{label} must be {length} lowercase hexadecimal characters")

    if not isinstance(prov, dict) or not isinstance(prov.get("source"), dict):
        raise ValueError("provenance and source must be objects")
    source = prov["source"]
    text(source.get("repository"), "source.repository")
    hexadecimal(source.get("commit"), 40, "source.commit")
    if "tag" in source:
        text(source["tag"], "source.tag")
        if source.get("ref", source["tag"]) != source["tag"]:
            raise ValueError("source.ref must match source.tag")
    seen = set()
    for section in ("copied", "pinned", "imports"):
        rows = prov.get(section, [])
        if not isinstance(rows, list):
            raise ValueError(f"{section} must be an array")
        for index, entry in enumerate(rows):
            label = f"{section}[{index}]"
            if not isinstance(entry, dict):
                raise ValueError(f"{label} must be an object")
            path(entry.get("upstream"), label + ".upstream")
            hexadecimal(entry.get("sha256"), 64, label + ".sha256")
            if "commit" in entry:
                hexadecimal(entry["commit"], 40, label + ".commit")
            if "upstreamSha256" in entry:
                hexadecimal(entry["upstreamSha256"], 64, label + ".upstreamSha256")
            if section != "imports" or "local" in entry:
                path(entry.get("local"), label + ".local")
                if entry["local"] in seen:
                    raise ValueError(f"duplicate local path: {entry['local']}")
                seen.add(entry["local"])
                if type(entry.get("size")) is not int or entry["size"] < 0:
                    raise ValueError(f"{label}.size must be a nonnegative integer")
            if "adjustment" in entry:
                adjustment_parts(entry["adjustment"])
    for group in ("strictDirs", "legacy", "owned"):
        if not isinstance(prov.get(group, []), list):
            raise ValueError(f"{group} must be an array")
        for item in prov.get(group, []):
            value = item.get("path") if isinstance(item, dict) else item
            path(value, group, prefix=group != "strictDirs")


def apply_adjustment(contents, adjustment):
    """The local bytes implied by an adjusted upstream copy; loud on mismatch."""
    kind, first, second = adjustment_parts(adjustment)
    if kind == "provenance-header":
        return first.encode("utf-8") + contents
    if kind == "import-retarget":
        olds, news = first, second
        for old, new in zip(olds, news):
            old, new = old.encode("utf-8"), new.encode("utf-8")
            if contents.count(old) != 1:
                raise ValueError("import-retarget: upstream line not found exactly once")
            contents = contents.replace(old, new)
        return contents
    raise ValueError(f"unknown adjustment kind {kind}")


def expected_local(upstream_bytes, entry):
    if "adjustment" in entry:
        return apply_adjustment(upstream_bytes, entry["adjustment"])
    return upstream_bytes


def check_local(prov):
    """Compare every copied and pinned file with its recorded digest and size."""
    errors = []
    listed = {}
    for section in ("copied", "pinned"):
        for entry in prov.get(section, []):
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
    """Local paths classified as copied, pinned, legacy or owned (prefixes end in /)."""
    exact = {entry["local"] for entry in prov.get("copied", []) + prov.get("pinned", [])}
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
        ["git", "--no-replace-objects", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def check_upstream(prov, repo):
    """Compare the pinned commits' bytes with the recorded digests and copies."""
    errors = []
    default_commit = prov["source"]["commit"]
    sections = prov.get("copied", []) + prov.get("imports", []) + prov.get("pinned", [])
    for commit in dict.fromkeys(e.get("commit", default_commit) for e in sections):
        exists = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if exists.returncode != 0:
            errors.append(f"pinned commit {commit[:12]}... is not in {repo}")
    source = prov["source"]
    if source.get("tag"):
        # The pin is a release tag (FAIR-bioHeaders-Specification#241): the
        # recorded tag must resolve to the recorded commit in the checkout.
        resolved = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo), "rev-parse", "--verify", "--quiet",
             f"refs/tags/{source['tag']}^{{commit}}"],
            capture_output=True, text=True,
        )
        if resolved.returncode != 0:
            errors.append(f"tag {source['tag']} is not in {repo} (fetch tags)")
        elif resolved.stdout.strip() != default_commit:
            errors.append(f"tag {source['tag']} resolves to {resolved.stdout.strip()[:12]}..., "
                          f"not the pinned {default_commit[:12]}...")
    if errors:
        return errors, 0
    checked = 0
    for entry in (prov.get("copied", []) + prov.get("imports", [])
                  + prov.get("pinned", [])):
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
            try:
                want = expected_local(data, entry)
            except ValueError as exc:
                errors.append(f"invalid adjustment for {entry['local']}: {exc}")
                continue
            if local.is_file() and local.read_bytes() != want:
                errors.append(f"local {entry['local']} differs from pinned "
                              f"{entry['upstream']} (adjustment re-applied)")
        checked += 1
    return errors, checked


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    comparison = parser.add_mutually_exclusive_group()
    comparison.add_argument(
        "--upstream", metavar="PATH",
        help="FAIR-bioHeaders-Specification checkout to compare against")
    comparison.add_argument(
        "--no-upstream", action="store_true",
        help="only check the recorded digests, even if a checkout is available")
    args = parser.parse_args(argv)

    prov = load_provenance()
    commit = prov["source"]["commit"]
    print(f"shared parity: pinned {prov['source']['repository']} {commit}")
    print(f"  {len(prov.get('copied', []))} copied files, "
          f"{len(prov.get('pinned', []))} frozen compatibility files, "
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
