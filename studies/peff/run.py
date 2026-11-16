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
from pathlib import Path

import bioheaders.cli
import pyteomics.fasta
import pyteomics.peff
from pyteomics import peff

ROOT = Path(__file__).resolve().parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def command(args, cwd=None):
    p = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )
    return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


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
    parser.add_argument("--validator-root", type=Path, required=True)
    parser.add_argument("--comet", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "results.json")
    args = parser.parse_args()
    if sys.byteorder != "little" or struct.calcsize("P") != 8:
        raise RuntimeError("Comet table probe requires little-endian 64-bit platform")
    for package, version in [("pyteomics", "5.0"), ("fair-bioheaders", "0.11.0")]:
        if importlib.metadata.version(package) != version:
            raise RuntimeError("Unexpected package version: " + package)
    pins = json.loads((ROOT / "sources.json").read_text())["files"]
    for label, module in [
        ("pyteomics-peff.py", pyteomics.peff),
        ("pyteomics-fasta.py", pyteomics.fasta),
        ("bioheaders-cli.py", bioheaders.cli),
    ]:
        if sha(Path(module.__file__).read_bytes()) != pins[label]["sha256"]:
            raise RuntimeError("Installed source differs from study pin: " + label)
    validator = args.validator_root.resolve() / "bin/PEFF/validatePEFF"
    obo = args.validator_root.resolve() / "var/CV/PSI-MOD.obo"
    comet = args.comet.resolve()
    result = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": {
            n: importlib.metadata.version(n) for n in ["pyteomics", "fair-bioheaders"]
        },
        "executableDigests": {
            str(p.name): sha(p.read_bytes()) for p in [validator, obo, comet]
        },
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
                    text = text.replace(
                        str(args.validator_root.resolve()), "<validator-root>"
                    )
                    record[tool][stream] = re.sub(
                        r"\(\d+s, \d+MB\)", "(timing/memory omitted)", text
                    )
            result["cases"][source.name] = record
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
