#!/usr/bin/env python3
"""Derive the chr4 fixture sequence files from an NCBI RefSeq delivery and measure them.

Part of FAIR-bioHeaders/FHP-Specification#29: it regenerates the two sequence
inputs that the released `fair-bioheaders` toolkit then received its headers
from, so the committed `chr4.fhr.fasta` and `chr4.fhp.fasta` are reproducible
from the published delivery rather than from a transcription.

Standard library only. Point ``--input-dir`` at a directory holding the three
source files named in ``SOURCES`` (downloaded whole; no ranged reads) and the
script verifies each against the digest recorded below before deriving anything:

  * the genomic slice is the ``NC_004353.4`` record of ``_genomic.fna.gz``,
    written verbatim (defline and sequence lines, as published);
  * the protein subset is the records of ``_protein.faa.gz`` whose identifier is
    a ``protein_id`` of some ``CDS`` feature whose seqid is ``NC_004353.4`` in
    ``_genomic.gff.gz``, written verbatim and in delivery order.

It prints one JSON object: the measurements quoted in ``README.md`` (record and
residue counts, base composition, masking, digests of everything it read and
wrote). It does not write FAIR-bioHeaders headers and does not compute the
FHR-family SHA-512/256 checksum: header authoring belongs to the toolkit
(``bioheaders combine``), and this script's digests are plain SHA-256 over whole
files, used only to pin the inputs.
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import sys

ACCESSION = "NC_004353.4"
PREFIX = "GCF_000001215.4_Release_6_plus_ISO1_MT"

# Measured on files downloaded from
# https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/215/GCF_000001215.4_Release_6_plus_ISO1_MT/
# on 2026-11-15; each was also checked against that delivery's md5checksums.txt.
SOURCES = {
    "genomic_fna_gz": {
        "name": PREFIX + "_genomic.fna.gz",
        "bytes": 44235956,
        "sha256": "e69e907b5e87ce756236dcef93e82001cfd08f1a0ed5f22e36cbbd3a87ebc57d",
    },
    "genomic_gff_gz": {
        "name": PREFIX + "_genomic.gff.gz",
        "bytes": 8688226,
        "sha256": "9a372f10f86f4fe4222d070a101716b7565affdd6cb96efae249e8afa3b2c726",
    },
    "protein_faa_gz": {
        "name": PREFIX + "_protein.faa.gz",
        "bytes": 9785243,
        "sha256": "4bf959b02c5b4c58accb36552e30bbf77f5088713b155ef4e02f4e6edc2d9dff",
    },
}


def digest(path):
    """(bytes, sha256) over the whole file as stored."""
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
            total += len(block)
    return total, h.hexdigest()


def check_inputs(input_dir):
    report = {}
    problems = []
    for key, want in SOURCES.items():
        path = os.path.join(input_dir, want["name"])
        if not os.path.exists(path):
            problems.append(f"missing input: {want['name']}")
            continue
        size, sha = digest(path)
        if size != want["bytes"] or sha != want["sha256"]:
            problems.append(f"{want['name']}: size {size} sha256 {sha} does not match "
                            f"the pinned size {want['bytes']} sha256 {want['sha256']}")
        report[key] = {"name": want["name"], "bytes": size, "sha256": sha}
    if problems:
        raise SystemExit("input verification failed:\n  " + "\n  ".join(problems))
    return report


def protein_ids_on_chromosome(gff_path):
    """protein_id values of CDS features whose seqid is the target accession."""
    ids = set()
    cds_lines = 0
    with gzip.open(gff_path, "rt", encoding="utf-8", newline="") as stream:
        for line in stream:
            if line.startswith("#") or not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 9 or cols[0] != ACCESSION or cols[2] != "CDS":
                continue
            cds_lines += 1
            found = re.search(r"(?:^|;)protein_id=([^;]+)", cols[8])
            if found:
                ids.add(found.group(1))
            else:
                raise SystemExit(f"{ACCESSION} CDS at {cols[3]}..{cols[4]} has no protein_id")
    return cds_lines, ids


def write_records_gzip(gzip_path, wanted, out_path):
    """Copy the FASTA records whose identifier is in `wanted`, verbatim bytes."""
    kept = 0
    total = 0
    with gzip.open(gzip_path, "rb") as src, open(out_path, "wb") as dst:
        keep = False
        for raw in src:
            if raw.startswith(b">"):
                total += 1
                keep = raw[1:].split()[0].decode("ascii") in wanted
                if keep:
                    kept += 1
            if keep:
                dst.write(raw)
    return total, kept


def write_genome_record(gzip_path, out_path):
    """Copy the target accession's record from the genomic FASTA, verbatim bytes."""
    records = 0
    with gzip.open(gzip_path, "rb") as src, open(out_path, "wb") as dst:
        capture = False
        for raw in src:
            if raw.startswith(b">"):
                records += 1
                capture = raw[1:].split()[0].decode("ascii") == ACCESSION
            if capture:
                dst.write(raw)
    return records


def measure_fasta(path):
    with open(path, "rb") as stream:
        data = stream.read()
    lines = data.decode("ascii").split("\n")
    deflines = [line for line in lines if line.startswith(">")]
    residues = "".join(line for line in lines if line and not line.startswith(">"))
    alphabet = {}
    for char in residues:
        alphabet[char] = alphabet.get(char, 0) + 1
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "deflines": deflines,
        "records": len(deflines),
        "residues": len(residues),
        "alphabet": dict(sorted(alphabet.items())),
        "ends_with_newline": data.endswith(b"\n"),
        "has_carriage_return": b"\r" in data,
        "sequence_line_lengths": sorted({len(line) for line in lines
                                         if line and not line.startswith(">")}),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input-dir", required=True,
                        help="directory holding the three pinned NCBI files")
    parser.add_argument("--output-dir", required=True,
                        help="where to write chr4_genomic.fna and chr4_proteins.faa")
    args = parser.parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)
    inputs = check_inputs(args.input_dir)

    cds_lines, wanted = protein_ids_on_chromosome(
        os.path.join(args.input_dir, SOURCES["genomic_gff_gz"]["name"]))
    genome_path = os.path.join(args.output_dir, "chr4_genomic.fna")
    protein_path = os.path.join(args.output_dir, "chr4_proteins.faa")
    genome_records = write_genome_record(
        os.path.join(args.input_dir, SOURCES["genomic_fna_gz"]["name"]), genome_path)
    protein_total, protein_kept = write_records_gzip(
        os.path.join(args.input_dir, SOURCES["protein_faa_gz"]["name"]), wanted, protein_path)

    genomic = measure_fasta(genome_path)
    proteins = measure_fasta(protein_path)
    upper = sum(n for c, n in genomic["alphabet"].items() if c in "ACGT")
    lower = sum(n for c, n in genomic["alphabet"].items() if c in "acgt")

    ids = [line[1:].split()[0] for line in proteins["deflines"]]
    checks = {
        "every pinned protein_id is present in the subset": set(ids) == wanted,
        "no protein record was kept twice": len(ids) == len(set(ids)),
        "defline is the target accession": genomic["deflines"][0].startswith(">" + ACCESSION),
        "the genomic slice holds exactly one record": len(genomic["deflines"]) == 1,
        "the protein subset kept as many records as it matched": protein_kept == len(ids),
    }
    print(json.dumps({
        "accession": ACCESSION,
        "inputs_verified": inputs,
        "gff": {"chr4_cds_lines": cds_lines, "chr4_unique_protein_ids": len(wanted)},
        "genomic_fna_records_in_delivery": genome_records,
        "protein_faa_records_in_delivery": protein_total,
        "genomic_slice": {
            **{k: v for k, v in genomic.items() if k != "alphabet"},
            "acgt_upper": upper,
            "acgt_lower": lower,
            "N_upper": genomic["alphabet"].get("N", 0),
            "n_lower": genomic["alphabet"].get("n", 0),
            "lowercase_fraction_of_acgt": round(lower / (upper + lower), 6),
        },
        "protein_subset": {
            **{k: v for k, v in proteins.items() if k != "alphabet"},
            "stop_characters": proteins["alphabet"].get("*", 0),
            "ambiguous_X_characters": proteins["alphabet"].get("X", 0),
            "lowercase_residues": sum(n for c, n in proteins["alphabet"].items()
                                      if c.islower()),
            "sample_deflines": proteins["deflines"][:3],
        },
        "checks": checks,
    }, indent=2))
    if not all(checks.values()):
        print("DERIVATION CHECK FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
