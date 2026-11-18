# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Read-only probes of locally installed, pinned readers; external binaries stay outside git."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def command(args, cwd=None):
    p = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )
    return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def verify_validator_archive(archive, pin, destination):
    """Check the downloaded validator archive against its pin, then extract it.

    Nothing from the archive runs before its size and SHA-256 match
    sources.json; extraction is done here (zipfile drops absolute and
    parent-directory member paths), not by an external unzip.
    """
    content = archive.read_bytes()
    if len(content) != pin["bytes"] or sha(content) != pin["sha256"]:
        raise RuntimeError(
            "Validator archive differs from study pin: "
            f"{len(content)} bytes, sha256 {sha(content)}"
        )
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(destination)
    return destination


def verify_comet(comet, pin, expected_sha256=None):
    """Check that the Comet binary was built from the pinned, unmodified source.

    The binary digest is build-specific, so the source checkout is the pin: the
    binary must sit in a git checkout whose HEAD is the pinned commit with no
    tracked-file changes. ``expected_sha256`` additionally pins one build when a
    rerun must use the same binary.
    """
    checkout = comet.parent
    head = command(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    if head["exit"] or head["stdout"].strip() != pin["commit"]:
        raise RuntimeError(
            "Comet binary is not inside a checkout of the pinned commit "
            + pin["commit"]
        )
    dirty = command(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"]
    )
    if dirty["exit"] or dirty["stdout"].strip():
        raise RuntimeError("Comet checkout has local changes to tracked files")
    digest = sha(comet.read_bytes())
    if expected_sha256 and digest != expected_sha256:
        raise RuntimeError("Comet binary differs from --comet-sha256: " + digest)
    return digest


def verify_perl_json(pin):
    """Check the one non-core Perl module the validator loads (JSON) before use."""
    found = command(["perl", "-MJSON", "-e", "print $JSON::VERSION"])
    if found["exit"] or found["stdout"].strip() != pin["version"]:
        raise RuntimeError(
            "Perl JSON module is not the pinned " + pin["version"] + ": "
            + (found["stdout"] or found["stderr"]).strip()
        )
    return found["stdout"].strip()


def peptide_table(content):
    # Pinned Comet v5 index, little-endian 64-bit build; footer gives raw-table start.
    if not content.startswith(b"Comet index database v5."):
        raise ValueError("Unexpected Comet index version")
    pos, end = struct.unpack("<qq", content[-16:])
    (count,) = struct.unpack_from("<Q", content, pos)
    pos += 8
    rows = []
    for _ in range(count):
        (length,) = struct.unpack_from("<i", content, pos)
        pos += 4
        sequence = content[pos : pos + length].decode("ascii")
        pos += length
        prev, nxt, mass, mod_filter, _ = struct.unpack_from("<ccdhq", content, pos)
        pos += 20
        rows.append([sequence, prev.decode(), nxt.decode(), mass, mod_filter])
    if pos != end:
        raise ValueError("Unexpected raw-table layout")
    return rows


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--validator-archive",
        type=Path,
        required=True,
        help="the downloaded ProteomicsPEFF.zip; checked against sources.json, "
        "then extracted to a temporary directory",
    )
    parser.add_argument(
        "--comet",
        type=Path,
        required=True,
        help="comet.exe built inside a clean checkout of the pinned Comet commit",
    )
    parser.add_argument(
        "--comet-sha256",
        help="optionally require this exact Comet binary digest (same build)",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "results.json")
    args = parser.parse_args()
    # The pinned experiment packages are imported here, not at module level, so
    # the unit suite can test the pin checks above without installing them.
    import bioheaders.cli
    import pyteomics.fasta
    import pyteomics.peff
    from pyteomics import peff

    if sys.byteorder != "little" or struct.calcsize("P") != 8:
        raise RuntimeError("Comet table probe requires little-endian 64-bit platform")
    for package, version in [("pyteomics", "5.0"), ("fair-bioheaders", "0.11.0")]:
        if importlib.metadata.version(package) != version:
            raise RuntimeError("Unexpected package version: " + package)
    sources = json.loads((ROOT / "sources.json").read_text())
    pins = sources["files"]
    for label, module in [
        ("pyteomics-peff.py", pyteomics.peff),
        ("pyteomics-fasta.py", pyteomics.fasta),
        ("bioheaders-cli.py", bioheaders.cli),
    ]:
        if sha(Path(module.__file__).read_bytes()) != pins[label]["sha256"]:
            raise RuntimeError("Installed source differs from study pin: " + label)
    comet = args.comet.resolve()
    comet_digest = verify_comet(comet, sources["Comet"], args.comet_sha256)
    perl_json = verify_perl_json(sources["perlModules"]["JSON"])
    extracted = tempfile.TemporaryDirectory(prefix="fhp-peff-validator-")
    validator_root = verify_validator_archive(
        args.validator_archive.resolve(), pins["validator-archive"], Path(extracted.name)
    )
    validator = validator_root / "bin/PEFF/validatePEFF"
    obo = validator_root / "var/CV/PSI-MOD.obo"
    extracted_pins = sources["validatorFiles"]
    for path, digest in [
        (validator, extracted_pins["bin/PEFF/validatePEFF"]),
        (obo, extracted_pins["var/CV/PSI-MOD.obo"]),
    ]:
        if sha(path.read_bytes()) != digest:
            raise RuntimeError("Extracted validator file differs from pin: " + path.name)
    result = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": {
            n: importlib.metadata.version(n) for n in ["pyteomics", "fair-bioheaders"]
        },
        "executableDigests": {
            validator.name: sha(validator.read_bytes()),
            obo.name: sha(obo.read_bytes()),
            comet.name: comet_digest,
        },
        "perlModules": {"JSON": perl_json},
        "cases": {},
    }
    with tempfile.TemporaryDirectory(prefix="fhp-peff-") as temp:
        tmp = Path(temp)
        generated = command([str(comet), "-p", "-q"], tmp)
        if generated["exit"]:
            raise RuntimeError(generated)
        params = (tmp / "comet.params.new").read_text()
        params = params.replace("peff_format = 0 ", "peff_format = 1 ")
        params = params.replace("peff_obo = ", f"peff_obo = {obo} ")
        params = params.replace(
            "spectral_library_name = /some/path/speclib.file", "spectral_library_name ="
        )
        (tmp / "comet.params").write_text(params)
        result["cometParameters"] = params.replace(
            str(obo), "<validator-root>/var/CV/PSI-MOD.obo"
        )
        for source in sorted(ROOT.glob("*.faa")):
            record = {}
            try:
                with peff.IndexedPEFF(str(source)) as reader:
                    record["pyteomics"] = {
                        "records": [
                            {"header": str(x.description), "sequence": x.sequence}
                            for x in reader
                        ],
                        "databaseBlocks": [dict(x) for x in reader.header_blocks],
                    }
            except ValueError as error:
                record["pyteomics"] = {
                    "error": type(error).__name__ + ": " + str(error)
                }
            record["validator"] = command(
                ["perl", str(validator), "--inputFile", str(source)]
            )
            record["bioheaders"] = command(
                [str(Path(sys.executable).parent / "bioheaders"), "verify", str(source)]
            )
            db = tmp / source.name
            db.write_bytes(source.read_bytes())
            record["comet"] = command(
                [str(comet), "-P" + str(tmp / "comet.params"), "-D" + str(db), "-j"],
                tmp,
            )
            index = Path(str(db) + ".idx")
            if index.exists() and record["comet"]["exit"] == 0:
                record["comet"]["peptides"] = peptide_table(index.read_bytes())
            # Normalize machine-specific paths/timing only; retain all diagnostics and exit codes.
            for tool in ["validator", "bioheaders", "comet"]:
                for stream in ["stdout", "stderr"]:
                    text = (
                        record[tool][stream]
                        .replace(str(ROOT), "<fixtures>")
                        .replace(temp, "<work>")
                    )
                    text = text.replace(str(validator_root), "<validator-root>")
                    record[tool][stream] = re.sub(
                        r"\(\d+s, \d+MB\)", "(timing/memory omitted)", text
                    )
            result["cases"][source.name] = record
    extracted.cleanup()
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
