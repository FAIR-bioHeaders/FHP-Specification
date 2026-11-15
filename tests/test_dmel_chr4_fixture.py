# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Integrity checks for the real-data chr4 FHR/FHP pair (issue #29).

Standard library plus PyYAML, like the rest of this suite. These are example
integrity checks, not conformance vectors: no `expected` outcome here is
consumed by `conformance/manifest.json`, and the numbers below are measurements
of the committed bytes recorded in
`examples/fhp/dmel-chr4/README.md`, not outputs of a validator under test.

What this guards:

* both files' SHA-512/256 checksums still equal what their own headers state,
  recomputed from the bytes with the repository's independent reader
  (`scripts/check_conformance.py`), so a line-ending or byte edit cannot slip in;
* the FHP `derivedFrom` parent digest equals the *recomputed* digest of the FHR
  file shipped beside it, which is the false-provenance failure #29 names: that
  check would pass a copied digest only if the bytes still produced it;
* the subset facts the headers assert (one genomic record of 1,348,131 bases,
  298 protein records, 319,099 residues, the soft-masked lower-case count, and
  the 17,000 `N` gap) still hold;
* the headers still cite the released v0.6.0 contracts (FHR 2.1, FHP 1.2).
"""

import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_conformance  # noqa: E402

FIXTURE = ROOT / "examples" / "fhp" / "dmel-chr4"
FHR = FIXTURE / "chr4.fhr.fasta"
FHP = FIXTURE / "chr4.fhp.fasta"

# Measured from NCBI's delivery on 2026-11-15 (see examples/fhp/dmel-chr4/README.md):
# the values below are the observations the headers were written from, so a
# change here is a change to the shipped sequence bytes or to a claim about them.
CHR4_BASES = 1_348_131
CHR4_ACGT_UPPER = 956_498
CHR4_ACGT_LOWER = 374_633
CHR4_GAP_N = 17_000
PROTEIN_RECORDS = 298
PROTEIN_RESIDUES = 319_099


def metadata_of(data: bytes) -> dict:
    """The header mapping, read the way tests/test_fhp_schema.py reads an FHP FASTA."""
    lines = data.decode("utf-8").splitlines()
    return yaml.safe_load("\n".join(line[2:] for line in lines if line.startswith(";~")))


def sequence_of(data: bytes) -> str:
    return "".join(line for line in data.decode("utf-8").splitlines()
                   if line and not line.startswith((";", ">")))


class FixturePresenceTests(unittest.TestCase):
    def test_both_files_are_present(self):
        for path in (FHR, FHP):
            self.assertTrue(path.is_file(), f"{path} is missing")


class ChecksumIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fhr_bytes = FHR.read_bytes()
        cls.fhp_bytes = FHP.read_bytes()

    def test_fhr_checksum_matches_its_own_bytes(self):
        stated, computed = check_conformance.fhr_checksum(self.fhr_bytes, "fasta")
        self.assertEqual(stated, computed, "chr4.fhr.fasta no longer matches its checksum")

    def test_metadata_inputs_match_generated_headers(self):
        for data, name in ((self.fhr_bytes, "metadata.fhr.yaml"),
                           (self.fhp_bytes, "metadata.fhp.yaml")):
            with self.subTest(metadata=name):
                header = metadata_of(data)
                header.pop("checksum")
                source = yaml.safe_load((FIXTURE / name).read_text(encoding="utf-8"))
                self.assertEqual(header, source)

    def test_fhp_checksum_matches_its_own_bytes(self):
        stated, computed = check_conformance.fhr_checksum(self.fhp_bytes, "fhp-fasta")
        self.assertEqual(stated, computed, "chr4.fhp.fasta no longer matches its checksum")

    def test_parent_link_equals_the_recomputed_fhr_checksum(self):
        _, recomputed = check_conformance.fhr_checksum(self.fhr_bytes, "fasta")
        header = metadata_of(self.fhp_bytes)
        parents = header["derivedFrom"]
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0]["headerType"], "FHR")
        self.assertEqual(parents[0]["relationship"], "translatedFrom")
        self.assertEqual(parents[0]["checksum"], recomputed,
                         "the FHP header does not point at the FHR file shipped here")

    def test_checksum_is_not_a_placeholder(self):
        # scripts/check_conformance.py treats this value as "not computed".
        self.assertNotIn(metadata_of(self.fhr_bytes)["checksum"],
                         check_conformance.PLACEHOLDER_CHECKSUMS)
        self.assertNotIn(metadata_of(self.fhp_bytes)["checksum"],
                         check_conformance.PLACEHOLDER_CHECKSUMS)


class ReleasedContractCitationTests(unittest.TestCase):
    """The pair cites the released contracts, and nothing that does not exist."""

    def test_fhr_cites_released_fhr_2_1(self):
        header = metadata_of(FHR.read_bytes())
        self.assertEqual(header["schema"], "https://w3id.org/fair-bioheaders/fhr/v0.6.0")
        self.assertEqual(header["schemaVersion"], "2.1")

    def test_fhp_cites_released_fhp_1_2(self):
        header = metadata_of(FHP.read_bytes())
        self.assertEqual(header["schema"], "https://w3id.org/fair-bioheaders/fhp/v0.6.0")
        self.assertEqual(header["schemaVersion"], "1.2")
        self.assertEqual(header["sourceType"], "database")
        self.assertNotIn("geneticCode", header,
                         "the delivery states no translation table; the field must stay absent")

    def test_both_headers_declare_the_subset_parentage(self):
        for path in (FHR, FHP):
            text = path.read_text(encoding="utf-8")
            self.assertIn("not a production reference", text, path.name)
        self.assertIn("chromosome 4 subset", FHR.read_text(encoding="utf-8"))


class MeasuredContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fhr_bytes = FHR.read_bytes()
        cls.fhp_bytes = FHP.read_bytes()

    def test_genomic_record_is_chr4_and_measured_length(self):
        text = self.fhr_bytes.decode("utf-8")
        deflines = [line for line in text.splitlines() if line.startswith(">")]
        self.assertEqual(deflines, [">NC_004353.4 Drosophila melanogaster chromosome 4"])
        bases = sequence_of(self.fhr_bytes)
        self.assertEqual(len(bases), CHR4_BASES)
        self.assertEqual(sum(1 for c in bases if c in "ACGT"), CHR4_ACGT_UPPER)
        self.assertEqual(sum(1 for c in bases if c in "acgt"), CHR4_ACGT_LOWER)
        self.assertEqual(bases.count("N"), CHR4_GAP_N)
        self.assertEqual(bases.count("n"), 0)
        header = metadata_of(self.fhr_bytes)
        self.assertEqual(header["masking"], "soft-masked")
        self.assertGreater(CHR4_ACGT_LOWER, 0, "soft-masked would be unsupported")

    def test_protein_subset_counts_match_the_header(self):
        text = self.fhp_bytes.decode("utf-8")
        deflines = re.findall(r"^>(\S+)", text, re.M)
        self.assertEqual(len(deflines), PROTEIN_RECORDS)
        self.assertEqual(len(set(deflines)), PROTEIN_RECORDS, "a protein record was duplicated")
        residues = sequence_of(self.fhp_bytes)
        self.assertEqual(len(residues), PROTEIN_RESIDUES)
        stats = metadata_of(self.fhp_bytes)["sequenceStats"]
        self.assertEqual(stats["sequenceCount"], len(deflines))
        self.assertEqual(stats["totalResidues"], len(residues))
        self.assertEqual(stats["geneCount"], 80)

    def test_protein_alphabet_is_the_deliverys(self):
        # No stop characters and no lower case in this delivery; one X residue.
        residues = sequence_of(self.fhp_bytes)
        self.assertNotIn("*", residues)
        self.assertEqual(residues.upper(), residues)
        self.assertEqual(residues.count("X"), 1)
        self.assertTrue(set(residues) <= set("ACDEFGHIKLMNPQRSTVWXY"))


if __name__ == "__main__":
    unittest.main()
