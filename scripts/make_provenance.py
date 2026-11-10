"""Generate SHA-256 provenance entries for the pinned FHP v0.5.0 artifacts."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DEFAULT_COMMIT = "170e677fbb6726a3f765373dbe1f214820000be7"
PINNED_FILES = (
    "fhp.json",
    "fhp_linkml.yml",
    "schemas/core.yaml",
    "schemas/shared.yaml",
    "schemas/versions.json",
    "docs/FHP.md",
    "docs/FORMAT.md",
    "docs/SCHEMA-VERSIONS.md",
    "conformance/manifest.json",
    "examples/fhp/example.fhp.fasta",
    "examples/fhp/minimal-database.fhp.json",
    "examples/fhp/minimal-mixed.fhp.json",
    "examples/fhp/minimal-predicted.fhp.json",
    "examples/fhp/rich-database.fhp.json",
    "examples/fhp/rich-mixed.fhp.yaml",
    "examples/fhp/rich-predicted.fhp.yaml",
)


def git(upstream, *args):
    return subprocess.run(
        ["git", "-C", str(upstream), *args],
        check=True,
        capture_output=True,
    ).stdout


def artifact_paths(upstream, commit):
    vectors = git(
        upstream,
        "ls-tree",
        "-r",
        "--name-only",
        commit,
        "--",
        "conformance/valid",
        "conformance/invalid",
    ).decode("utf-8").splitlines()
    vectors = [
        path
        for path in vectors
        if Path(path).name.startswith("fhp-fasta-")
        and path.endswith(".fhp.fasta")
    ]
    return sorted((*PINNED_FILES, *vectors))


def generate_entries(upstream, commit, core_target="schemas/core.yaml"):
    entries = []
    for path in artifact_paths(upstream, commit):
        contents = git(upstream, "show", f"{commit}:{path}")
        if path == "fhp.json":
            targets = ("fhp.json", "tests/fixtures/releases/fhp-v0.5.0.json")
        elif path == "schemas/core.yaml":
            targets = (core_target,)
        else:
            targets = (path,)
        digest = hashlib.sha256(contents).hexdigest()
        entries.extend(
            {"local": target, "upstream": path, "sha256": digest}
            for target in targets
        )
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--upstream", type=Path, required=True, help="shared-spec checkout"
    )
    parser.add_argument(
        "--commit", default=DEFAULT_COMMIT, help="immutable shared commit"
    )
    parser.add_argument(
        "--core-target",
        choices=("schemas/core.yaml", "schemas/core-v0.5.yaml"),
        default="schemas/core.yaml",
        help="local path chosen for the pinned shared core",
    )
    parser.add_argument(
        "--output", type=Path, help="output JSON file (default: stdout)"
    )
    args = parser.parse_args(argv)
    entries = generate_entries(args.upstream, args.commit, args.core_target)
    output = json.dumps(entries, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
