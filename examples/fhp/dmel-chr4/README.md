# chr4 real-data FHR/FHP fixture (Drosophila melanogaster GCF_000001215.4)

Fixture pair for
[#29](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/29): the first
FHP example in this repository derived from published data instead of being
written as a synthetic placeholder.

| File | What it is |
| --- | --- |
| `chr4.fhr.fasta` | FHR parent, `schemaVersion` 2.1. One sequence record: chromosome 4 (`NC_004353.4`), 1,348,131 bases. 1,368,548 bytes, SHA-256 `7090495ffede5240a170d97175f0f713a61b65d0345dafbc7665199c2045674d`. |
| `chr4.fhp.fasta` | FHP child, `schemaVersion` 1.2. The 298 protein records this annotation places on that chromosome. 350,785 bytes, SHA-256 `e517b8df07174108a35e50180528f5ed348658960ba06d3777fe36556d4f0f67`. |
| `metadata.fhr.yaml`, `metadata.fhp.yaml` | The metadata inputs handed to `bioheaders combine`. The headers in the two FASTA files are the toolkit's output; no header line and no checksum was written by hand. |
| `derive_chr4.py` | Rebuilds both sequence inputs from the delivery, verifying the pinned source digests first, and prints the measurements quoted here. Standard library only. |
| `README.md` | This record. |

**This is a pilot and teaching artifact, not a production reference.** The FHR
parent is a single-chromosome subset, so the `derivedFrom` checksum carried by
`chr4.fhp.fasta` describes that subset and nothing else. A production protein set
taken from this assembly links the whole-assembly FHR instead. Both headers say
this in their `documentation` field.

**Classification: example, not conformance vector.** Nothing was added to
`conformance/` or to `conformance/manifest.json`, which stays at 77 vectors. A
vector's `expected` outcome has to be reviewed independently rather than produced
by the same derivation that produced the fixture. If a reviewer wants a vector
from this pair, propose it separately and have someone who did not write this
derivation sign off on the expected outcome.
`tests/test_dmel_chr4_fixture.py` is an example-integrity guard (the committed
bytes still match their own headers and their own parent link), which is a
different claim from a normative vector.

## Licensing

Two separate terms, kept apart deliberately.

- The sequence bytes are the NCBI RefSeq delivery of `GCF_000001215.4` and are
  **not relicensed** here. Neither the delivered GenBank record for
  `NC_004353.4` nor the delivery's `README.txt` states a license, so
  `reuseConditions` in both headers says that plainly rather than asserting a
  grant. That record also names several submitters (FlyBase Consortium, Berkeley
  Drosophila Genome Project, Celera Genomics, Drosophila Heterochromatin Genome
  Project), so no single employment-typed term is claimed for the sequence.
- The header fields, this document, `derive_chr4.py`, the test and the other
  repository files this work touches are MPL-2.0 FAIR-bioHeaders contributions
  from March 2025 onward, under the repository
  [LICENSE](../../../LICENSE). Nothing in the historical USDA public-domain part
  of that split was rewritten and no previously distributed version was
  relabeled.

## Donor, as verified on 2026-11-15

Every value below was read from NCBI on the retrieval date. None of it was taken
from the issue text on trust.

| Value | Measured from |
| --- | --- |
| `GCF_000001215.4`, assembly name `Release 6 plus ISO1 MT`, description "Release 6 plus ISO1 mitochondrial genome" | `esearch.fcgi?db=assembly&term=GCF_000001215.4` → `count: 1`, `idlist: ["202931"]`; then `esummary.fcgi?db=assembly&id=202931` |
| uid `202931` | that esearch `idlist`, not a guessed uid |
| organism `Drosophila melanogaster`, taxid `7227` | `_assembly_report.txt` (`# Organism name`, `# Taxid`); GFF directive `##species https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=7227`; GenBank source feature `/db_xref="taxon:7227"` |
| assembly level Chromosome, type haploid, BioSample `SAMN02803731`, BioProject `PRJNA13812`, submitter "The FlyBase Consortium/Berkeley Drosophila Genome Project/Celera Genomics", date 2014-08-01, synonym `dm6` | `esummary` plus the `_assembly_report.txt` header |
| GenBank `GCA_000001215.4`, "RefSeq assembly and GenBank assemblies identical: yes", both FTP paths published | `_assembly_report.txt`; `esummary` `ftppath_refseq` = `ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/215/GCF_000001215.4_Release_6_plus_ISO1_MT` |
| annotation source FlyBase Release 6.54 | GFF directive `#!annotation-source FlyBase Release 6.54`; the GenBank `##Genome-Annotation-Data` block (`Annotation Provider :: FlyBase`, `Annotation Status :: Full annotation`, `Annotation Version :: Release 6.54`) |
| chromosome 4 row: name `4`, role `assembled-molecule`, molecule `4`, location/type `Chromosome`, GenBank `AE014135.4`, relationship `=`, RefSeq `NC_004353.4`, unit `Primary Assembly`, length `1348131`, UCSC `chr4` | `_assembly_report.txt`, line 35 |
| assembly-wide counts: 13,962 protein-coding genes, 30,802 CDS-with-protein | `_feature_count.txt`, `all` rows |
| molecule record: `slen` 1348131, title "Drosophila melanogaster chromosome 4", taxid 7227 | `esummary.fcgi?db=nuccore&id=NC_004353.4` |
| BioSample `SAMN02803731`: uid 2803731 (from `esearch&db=biosample`, `count: 1`), sample name and title `iso-1`, owner "Lawrence Berkeley National Laboratory", contact Sue Celniker, package `Model.organism.animal.1.0`, submitted 2014-05-29, live 2014-07-23, attributes strain iso-1, tissue whole embryo, dev_stage embryos, sex mixed, biomaterial provider "Roger Hoskins and Gerry Rubin", genotype identical to the GenBank source feature, link BioProject `PRJNA13812`, comment naming Adams et al 2000 (PubMed 10731132) | `efetch.fcgi?db=biosample&id=2803731&rettype=xml`; control `esearch&db=biosample&term=SAMN99999999` → `count: 0` |
| the 17,000 `N` characters are one `within_scaffold` gap at `NC_004353.4:1200663-1217662` with `map` linkage evidence, and the only gap row for this accession | `_genomic_gaps.txt.gz` |
| metadataAuthor ORCID `0000-0003-3192-6538` resolves to given name "David", family name "Molik" | `pub.orcid.org/v3.0/0000-0003-3192-6538/person` |

Controls run alongside the positive probes:

- `esearch` for `GCF_999999999.9_NOTREAL` returns `count: 0` with an empty
  `idlist`, so the `count: 1` above discriminates.
- `esummary` for `NC_9999999.9` returns `"Invalid uid ... at position= 0"` with
  `uids: []`, so the successful `NC_004353.4` summary discriminates.
- `HEAD` on a nonsense name in the delivery directory returns 404 while the real
  names return 200 with `content-type: application/x-gzip`.
- The trap named in the issue is real: `..._ISO1_MT/_protein.faa.gz` (slash form)
  returns an HTML error page, while `..._ISO1_MT_protein.faa.gz`
  (underscore-joined) is the file. Names were taken from a directory listing
  rather than constructed.
- Every `.gz` was downloaded whole and passed `gzip -t` before being read. No
  ranged read was used for any content or digest claim: a ranged read of a gzip
  member truncates mid-stream and makes a healthy file look empty.
- NCBI **web-page** status codes are not used as evidence anywhere.
  `https://www.ncbi.nlm.nih.gov/nuccore/...` answered 200 for the real accession
  and also 200 for the invented `NC_9999999.9`, because the page renders
  client-side. Those URLs appear only as `relatedLink` locators; every existence,
  length and content claim comes from eutils JSON or from FTP bytes, with the
  controls above.
- `ORCID` control: `pub.orcid.org/v3.0/0000-0000-0000-0000/person` returns 404.

### Correction to the sizes quoted in the issue

The issue recorded `_feature_count.txt` 627 B and `_assembly_stats.txt` 2,323 B
from a batch of `HEAD` probes. Those were gzip-encoded transfer lengths, not file
sizes: with `Accept-Encoding: identity` the same URL reports 3,929 B, and the
bytes actually downloaded are 3,929 B and 16,501 B with MD5s matching
`md5checksums.txt`. `_rna.fna.gz` (23,529,984 B) and
`_rna_from_genomic.fna.gz` (17,310,353 B) are two different files, both present.
Every size in the table below comes from bytes on disk.

## Source files: size, digest, role

Retrieved 2026-11-15 with `curl --fail` from
`https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/215/GCF_000001215.4_Release_6_plus_ISO1_MT/`
(prefix abbreviated to `P_`). Each byte count is what was downloaded, each
SHA-256 is over the whole compressed file, and each MD5 was compared with that
directory's own `md5checksums.txt`.

| File | Bytes | SHA-256 | MD5 vs `md5checksums.txt` | Role here |
| --- | --- | --- | --- | --- |
| `P_protein.faa.gz` | 9,785,243 | `4bf959b02c5b4c58accb36552e30bbf77f5088713b155ef4e02f4e6edc2d9dff` | `d0a81857fd1aa796ff9236cbd5105ab0` matches | source of the FHP protein records |
| `P_genomic.fna.gz` | 44,235,956 | `e69e907b5e87ce756236dcef93e82001cfd08f1a0ed5f22e36cbbd3a87ebc57d` | `869cf40e4f5c7ca27d04ca9ae7baee4f` matches | source of the FHR chromosome 4 record |
| `P_genomic.gff.gz` | 8,688,226 | `9a372f10f86f4fe4222d070a101716b7565affdd6cb96efae249e8afa3b2c726` | `1de22f17786c44ae98d7922116967b4e` matches | authority for which CDS lie on `NC_004353.4` |
| `P_cds_from_genomic.fna.gz` | 10,674,857 | `3f379cec1d952f9a1c22e2b6dd9ff8eefce6da97ffb198cde93dc0a17c40da01` | `c3ea3177b4f55f92fa0fd0f6a89468ce` matches | independent cross-check of the member list |
| `P_feature_table.txt.gz` | 1,931,886 | `03303033ae31a203e11c5a0acdb69c10f4d72b4be52e7df09c45a8bf1b415148` | `6befcb79efbef05e99598d43f4ff2317` matches | third count of chr4 CDS; checked for translation-table statements |
| `P_genomic.gbff.gz` | 73,106,228 | `d010fd478e36938af0dbbc14f08aa543092e44e1e9d19f72b80f3e47a9c9bbc7` | `1fba6caf70e5884378217c12b48db76d` matches | GenBank source record: qualifiers, references, annotation block |
| `P_assembly_report.txt` | 214,116 | `22bf2cefea3bf4abc56aab340bdfb32f27dcd02b78f57c0762f8f1036e7963e7` | `ecb1db60e27f4f5ce3dd35fa46b4d7c6` matches | molecule accession, role, type, length |
| `P_assembly_stats.txt` | 16,501 | `e91c3716c57d5b0d8b946c94e4fbfd9bac74405e927f053d3baadbdd704adaa8` | `cc2c9939aef3f92c5f88aa8d20fab11b` matches | chr4 total and ungapped length, spanned gaps, GC |
| `P_feature_count.txt` | 3,929 | `1bcc2d12804490dd10452dc9d98ca42c7125ccc2591dad0603ee9783c671d76d` | `390ad2968539bd08d44810c8986fc188` matches | assembly-wide feature counts |
| `P_genomic_gaps.txt.gz` | 5,753 | `e993042891ae03def7e2e32c559e23cd34c8692ba677ff12a4026d93ddd18041` | `4ae57f7ed15d7b5dba73a603439f4eaf` matches | localises the chr4 gap behind the measured `N` run |
| `md5checksums.txt` | 5,747 | `148f87060005d84a397d74a216cca8454d0f37bd8928be5ac9517169439c9fa1` | (it is the control) | integrity control for the compressed files |
| `uncompressed_checksums.txt` | 3,045 | `edbc2647a9f35bca7c2695efde8690d65166249423b9d693ea0aefce635d632c` | (it is the control) | integrity control for decompressed bytes |
| `annotation_hashes.txt` | 410 | `8440fb061a189d21cc26f7d7db70d1daba6b242e17a3292ed480ccf2c1374ccc` | `39ccfa6b343adc57b5dd6672948403a5` matches | annotation last-changed date (2023-12-27) |

Server `Last-Modified` on the files used: `P_protein.faa.gz`,
`P_genomic.gff.gz`, `P_cds_from_genomic.fna.gz`, `P_feature_table.txt.gz`,
`P_genomic.gbff.gz` and `P_feature_count.txt` 2023-12-27; `P_genomic.fna.gz`
2014-10-31; `P_assembly_report.txt` and `P_assembly_stats.txt` 2024-08-30.

Self-consistency: `P_protein.faa.gz` was digested through two independent code
paths and reproduced exactly, as were the two committed fixture files.

```text
$ shasum -a 256 P_protein.faa.gz
4bf959b02c5b4c58accb36552e30bbf77f5088713b155ef4e02f4e6edc2d9dff
$ python3 -c "import hashlib; ..."        # 1 MiB streaming loop
4bf959b02c5b4c58accb36552e30bbf77f5088713b155ef4e02f4e6edc2d9dff
```

Decompression integrity: the whole `P_genomic.fna` stream measures 145,657,746
bytes, MD5 `a201b53b7eab2eb161671e4b3ae670a0`, CRC32 `4f7038a4`, equal to the
`uncompressed_checksums.txt` row for that path. That is what licenses every claim
below about bytes sliced out of it.

## Derived sequence inputs

`derive_chr4.py` writes these two files and stops if any pinned input digest
differs. They are not committed: they are the delivery's bytes, reproducible from
the digests above, and committing them would duplicate 1.7 MB a second time. They
are also exactly what `bioheaders strip` returns from the committed pair, which is
the check that the toolkit added only header lines.

| Derived file | Bytes | SHA-256 |
| --- | --- | --- |
| `chr4_genomic.fna` — the `NC_004353.4` record, defline and sequence lines verbatim | 1,365,033 | `9ea85183fc77137381a6e81adf8f088c84c68a888dc323ef8b286b4ef165e184` |
| `chr4_proteins.faa` — 298 records verbatim, delivery order | 345,485 | `9fe5e0f8d2f42633d6cbc66e927c9f5d41873b71e1603299935084d08c28fa5b` |

## The chr4 selection rule, and the count it produced

Rule, stated exactly:

1. Take every `CDS` line of `_genomic.gff.gz` whose seqid is `NC_004353.4`. That
   is 2,743 lines (a CDS occupies one line per exon segment), carrying 298
   distinct `protein_id` values. `derive_chr4.py` fails if any chr4 CDS has no
   `protein_id`, so the member set cannot shrink unnoticed.
2. Read `_protein.faa.gz` and keep, verbatim and in delivery order, every record
   whose identifier — the first whitespace-delimited token of the defline — is one
   of those 298 accessions.
3. Result as measured: **298 records**, 319,099 residues, 345,485 bytes.

The protein FASTA carries no location information, contrary to the assumption in
the issue text. Its deflines read
`>NP_001014685.1 pangolin, isoform H [Drosophila melanogaster]` — accession,
product name, organism — and the string `NC_004353` occurs **0** times in the
file. Membership cannot be read off `_protein.faa.gz` at all, so the GFF3 is the
authority and the two checks below are what make that safe.

| Independent check | Measured |
| --- | --- |
| `P_cds_from_genomic.fna.gz` record ids of the form `lcl\|NC_004353.4_cds_<acc>_<n>` | 298 records; the `<acc>` set equals the GFF set, 0 missing and 0 extra |
| `P_feature_table.txt.gz` rows with `genomic_accession == NC_004353.4` and `feature == CDS` | 298 rows, 298 distinct `product_accession` values (same molecule: 298 `mRNA` rows, 114 `gene` rows) |
| `P_protein.faa.gz` | 30,802 records; all 298 wanted ids found exactly once; no duplicates; none absent |
| `P_genomic.gbff.gz`, record `NC_004353.4` | 298 `protein_id`, 298 `translation` and 298 `codon_start` qualifiers |
| assembly-wide | 30,802 protein records equals the `CDS with_protein` count in `_feature_count.txt` |

Linkage measured for `sequenceStats`: those 298 CDS sit on 298 transcript features
whose parents are 80 distinct `gene` features, every one of them
`gene_biotype=protein_coding`, with up to 12 annotated transcripts per gene (11
genes have one). 287 of the 298 deflines name an isoform explicitly.

## Masking and length, measured on the bytes that shipped

Over the `NC_004353.4` record as it appears in `_genomic.fna.gz`, which is what
`chr4.fhr.fasta` carries:

| Measurement | Value |
| --- | --- |
| Bases | 1,348,131 |
| ACGT upper case | 956,498 |
| ACGT lower case | 374,633 — 28.144 % of the 1,331,131 ACGT characters |
| `N` | 17,000 upper case; lower-case `n`: 0 |
| Other characters | none (no ambiguity codes beyond `N`) |
| GC over A+T+G+C | 35.25 % |
| Line structure | 80-character lines with a 51-character final line, LF endings, trailing newline, no CR |

Cross-checks: `_assembly_stats.txt` for `Primary Assembly 4 Chromosome all` gives
total-length 1,348,131 and ungapped-length 1,331,131 with 1 spanned gap, so
1,348,131 − 1,331,131 = 17,000 is exactly the measured `N` count — the only `N`
run is the gap NCBI itself reports. `_genomic_gaps.txt.gz` (5,753 B, SHA-256
`e993042891ae03def7e2e32c559e23cd34c8692ba677ff12a4026d93ddd18041`, MD5
`4ae57f7ed15d7b5dba73a603439f4eaf` matching `md5checksums.txt`) localises that
gap precisely: `NC_004353.4 1200663 1217662 17000 within_scaffold map`, and it is
the only row for this accession. `_assembly_stats.txt`'s `gc-perc 35` matches the
measured 35.25 %. The GFF directive `##sequence-region NC_004353.4 1 1348131`, the
`_assembly_report.txt` length column, the GenBank `LOCUS` line
(`NC_004353 1348131 bp DNA linear CON 26-DEC-2023`), `esummary` `slen` and the
bytes in the file all give the same length, and the defline
`>NC_004353.4 Drosophila melanogaster chromosome 4` matches the report row and the
`esummary` title.

`masking: soft-masked` is the only value the bytes support. `hard-masked` is
contradicted by 374,633 lower-case bases, `not-masked` by the same measurement,
and `repeat-masked` would additionally assert which agent produced the masking,
which the delivery does not document.

An independent slice check also found a difference worth recording. NCBI also publishes this
molecule on its own at
`P_assembly_structure/Primary_Assembly/assembled_chromosomes/FASTA/chr4.fna.gz`
(378,797 B compressed, 1,365,033 B uncompressed, MD5
`edd1c69d6360fe22ee850c3bca51894b`, CRC32 `aac02d3f`, both reproduced from
`uncompressed_checksums.txt`). Compared with the slice above: identical defline,
identical byte length, identical sequence ignoring case, and 374,633 differences
that are all case-only — because **that** copy is unmasked (0 lower-case
characters) while the `_genomic.fna.gz` copy is soft-masked. The same molecule
reaches you in two masking states depending on which file you download, which is
why masking was measured on the shipped bytes rather than looked up. This fixture
ships the `_genomic.fna.gz` version.

## Authoring and verification with the released toolkit

`fair-bioheaders` 0.11.0 from PyPI in a throwaway venv; no toolkit working tree was
used.

```text
$ python3 -m venv bh0110 && ./bh0110/bin/python -m pip install "fair-bioheaders==0.11.0"
$ ./bh0110/bin/bioheaders --version
0.11.0
$ ./bh0110/bin/python -V
Python 3.15.0
```

The cited contracts are the released ones, and the toolkit's bundled copies are
byte-equal to the `v0.6.0` tag of FAIR-bioHeaders-Specification:

| Contract | Bundled copy in 0.11.0 | Raw file at tag `v0.6.0` |
| --- | --- | --- |
| FHP 1.2 | `bioheaders/schemas/fhp-1.2.json` `92a0b3cbcfe69939ebfaac69f0c5958ce426c005873efe8d3e3eb0fc0dab6de5` | `92a0b3cbcfe69939ebfaac69f0c5958ce426c005873efe8d3e3eb0fc0dab6de5` |
| FHR 2.1 | `bioheaders/schemas/fhr-2.1.json` `694ab5afaf8c3743eacf9e2aacb5551f7cbe37073b6f4afc3ae4a65b47f9d4df` | `694ab5afaf8c3743eacf9e2aacb5551f7cbe37073b6f4afc3ae4a65b47f9d4df` |

```sh
BH=./bh0110/bin/bioheaders
$BH combine --type fasta metadata.fhr.yaml chr4_genomic.fna   -o chr4.fhr.fasta
$BH convert --from fasta --to json chr4.fhr.fasta -           # the parent digest is this output
$BH combine --type fasta metadata.fhp.yaml chr4_proteins.faa  -o chr4.fhp.fasta
```

`combine` computed both `checksum` values. The `derivedFrom` checksum in
`metadata.fhp.yaml` is the value the toolkit reported for `chr4.fhr.fasta`, read
out of the built file rather than transcribed from an earlier run. Rebuilding both
files from the committed metadata and the derived inputs reproduced the committed
bytes exactly:

```text
$ cmp chr4.fhr.fasta rebuild.fhr.fasta    # silent: identical
$ cmp chr4.fhp.fasta rebuild.fhp.fasta    # silent: identical
```

### Tool output

```text
$ bioheaders verify chr4.fhr.fasta
Checksum verified.
$ bioheaders verify chr4.fhp.fasta
Checksum verified.
$ bioheaders validate chr4.fhr.fasta
FHR metadata is valid.
$ bioheaders validate chr4.fhp.fasta
FHP metadata is valid.
$ bioheaders verify-links chr4.fhp.fasta chr4.fhr.fasta
derivedFrom[0] FHR translatedFrom: matched (chr4.fhr.fasta)
A match confirms file identity only, not that the translations are correct.
exit=0
$ bioheaders verify-links --require-all chr4.fhp.fasta chr4.fhr.fasta
derivedFrom[0] FHR translatedFrom: matched (chr4.fhr.fasta)
A match confirms file identity only, not that the translations are correct.
exit=0
$ bioheaders strip chr4.fhr.fasta - | cmp - chr4_genomic.fna    # silent: identical
$ bioheaders strip chr4.fhp.fasta - | cmp - chr4_proteins.faa   # silent: identical
```

The headers were also validated with `jsonschema` 4.26.0
(`Draft202012Validator` with `FormatChecker`) against the raw contract bytes
fetched from the `v0.6.0` tag, independently of the toolkit: 0 errors for each.

### Independent re-derivation of the checksums

The header value was re-derived with standard-library `hashlib` alone, from
`docs/FORMAT.md` R1–R5 read off the pinned copy in this repository: take the file
as bytes, exclude the root `;~checksum:` line **and** its terminator, apply
SHA-512/256 to every other byte, encode as standard padded base64. This shares no
code with the toolkit that wrote the value, so it is not the toolkit being asked
to agree with itself. The snippet below is the compact form valid for these two
toolkit-written files (unindented `checksum` key, plain unquoted value, LF
endings); `scripts/check_conformance.py` implements the general rule and
reproduces the same three digests.

```python
import base64, hashlib
def recheck(path):
    data = open(path, "rb").read()
    lines = data.splitlines(keepends=True)
    idx = next(i for i, l in enumerate(lines) if l.startswith(b";~checksum: "))
    stated = lines[idx].split(b": ", 1)[1].strip().decode()
    body = b"".join(lines[:idx] + lines[idx + 1:])
    return stated, base64.b64encode(hashlib.new("sha512_256", body).digest()).decode()
```

```text
examples/fhp/dmel-chr4/chr4.fhr.fasta
  file bytes 1368548  hashed bytes 1368491
  stated     fHGkIi8u8lJCJstnJoQXM7XsXp/HXEyOe6y8GyGZO1k=
  recomputed fHGkIi8u8lJCJstnJoQXM7XsXp/HXEyOe6y8GyGZO1k=   agree True
examples/fhp/dmel-chr4/chr4.fhp.fasta
  file bytes 350785  hashed bytes 350728
  stated     pOu7KAKSHg5tOw0snOEZ69I7T7Q/BpVpxiyTAp7bPg8=
  recomputed pOu7KAKSHg5tOw0snOEZ69I7T7Q/BpVpxiyTAp7bPg8=   agree True

# same code, on files with known outcomes
examples/fhp/example.fhp.fasta                          agree True
conformance/valid/fhp-fasta-rich.fhp.fasta              agree True
conformance/invalid/fasta-sequence-tampered.fhr.fasta
  stated     3an6Cqo2eomqlt75XIpyWXDtls3GhA8EOpjK97S+ykc=
  recomputed Kdqmb+HXtbPotft0QmYzADuNEEOduWBqTndOu8WNw20=  agree False
```

`tests/test_dmel_chr4_fixture.py` keeps the load-bearing parts of this running in
CI: both checksums recomputed from the committed bytes, `derivedFrom` compared
against the recomputed parent digest, and the measured record, residue, base,
lower-case and `N` counts. Mutation controls confirm the guard is not vacuous:
changing one sequence base near the end of either file, or one letter inside a
header scalar, makes stated and recomputed disagree, and substituting the
well-formed 44-character digest of a *different* FHR-family file into
`derivedFrom` breaks the parent-link comparison without making the value
malformed.

### The false-provenance control

The failure mode #29 names — a file that verifies cleanly while pointing at a
parent nobody shipped — was reproduced deliberately. The same chr4 protein body
was combined against metadata whose `derivedFrom.checksum` is a genuine
FHR-family digest of a different file (this repository's pinned
`examples/fhp/example.fhp.fasta`, `BchVe2rk283HC1rFZqbg355ht825/seaOoIAFFMY7VI=`):

```text
$ bioheaders verify wrong-parent.fhp.fasta
Checksum verified.                      # self-checksum still passes
$ bioheaders verify-links wrong-parent.fhp.fasta chr4.fhr.fasta
derivedFrom[0] FHR translatedFrom: not matched (chr4.fhr.fasta has checksum fHGkIi8u8lJCJstnJoQXM7XsXp/HXEyOe6y8GyGZO1k=)
chr4.fhr.fasta: not a recorded parent
exit=3
```

`verify` alone therefore cannot detect a wrong parent, so the pair is only
meaningful when both commands are run, as they were above on the committed files.
The control file was left out of the commit.

## Header-block format rules

Checked on the committed files, because a FASTA header is a fragile place to put
text: all `;~` lines precede the first `>` line (R10 — 59 header lines in the FHR
and 85 in the FHP, none after the first record); no `;~` line contains a raw `>`
or `@` (R11); both headers are pure ASCII, so they cannot contain U+0085, U+2028
or U+2029 (R6); no byte-order mark (R7); no duplicate top-level keys, anchors,
aliases or merge keys (R8); exactly one root-level `;~checksum:` line each (R2);
LF endings with no CR anywhere, and each file ends with a newline (R1).

## What the headers claim, and what they do not

Populated from the source rather than asserted: `taxon` (record `ORGANISM` and
`/db_xref="taxon:7227"`), `accessionID`, `identifier` (the `NCBI_Assembly:` CURIE
appears verbatim as the GFF's `genome-build-accession` directive; the molecule
accessions come from the report row), `scholarlyArticle` in the FHR
(`10.1101/gr.185579.114`, "The Release 6 reference sequence of the Drosophila
melanogaster genome", which is `REFERENCE 3` of the GenBank record for
`NC_004353.4`; the DOI was resolved from that PubMed id 25589440 and not
guessed), `voucherSpecimen` (BioSample `SAMN02803731` from the record's `DBLINK`,
plus the source feature's `/genotype`, with an explicit note that no physical
voucher accession is stated), `source`, `sequenceStats` and `isoformPolicy`.
`assemblyAuthor` is the `_assembly_report.txt` `# Submitter:` line verbatim, as an
Organizational name.

`metadataAuthor` is the repository maintainer, David C Molik, with the ORCID
above, following the pattern of the reviewed FHR pilot in FHT-Specification. The
derivation was executed by an agent session on the maintainer's instruction. If
reviewers want a different attribution, it is one line in each metadata file — but
both files must then be rebuilt and re-verified, because changing the FHR header
changes its checksum and therefore the FHP's `derivedFrom`.

Deliberately absent, each with the reason in the header's `documentation`:

- `geneticCode`. The delivery states no translation table for these CDS: the GFF
  gives `codon_start` with no `transl_table`, the feature table's `attributes`
  column is empty for all 298 chr4 CDS, and the GenBank record carries a
  `transl_except` qualifier without naming a table. An unstated table is not an
  asserted one, and FHP forbids inferring one.
- `predictionSoftware`, `predictionProtocol`: the record attributes these models
  to FlyBase curation without naming a pipeline or version.
- `completeness`: no BUSCO run was performed on this subset.
- FHP `accessionID`, FHP `scholarlyArticle`: a single-chromosome subset of an
  annotation has no accession and no publication of its own.
- FHR `vitalStats`, `seqcol_id`, `instrument`, `assemblySoftware`,
  `assemblyProtocol`, `funding`: the published statistics and platform statements
  describe the whole assembly rather than this slice, and a SeqCol digest is a
  supplied value that nobody supplied here (FHR stores it and never computes it).

Two measured specifics are recorded rather than normalised away. The subset contains
exactly one `X` residue, at position 544 of the 655-residue `NP_001368990.1`
(*twin of eyeless*, isoform D); the GenBank record explains it with
`/transl_except=(pos:1006158..1006160,aa:OTHER)` on that CDS, and the residue
ships unchanged. And none of the 298 records carries a terminal `*` — 0 stop
characters anywhere in 319,099 residues — which is what this delivery looks like;
nothing was added to make it look like a different convention.

## Where this lives, and the pin it exposes

See [docs/DEVELOPMENT-TREE.md](../../../docs/DEVELOPMENT-TREE.md#real-data-example-fixture-issue-29)
for the classification. In short: this directory is classified FHP-owned in
`provenance.json` and `examples/fhp/**` is `-text` in `.gitattributes`.

When this fixture was written (#30) this tree's pinned copies were FHP 1.1 and
the frozen legacy FHR 1.0, so the repository's own example gate could not
schema-validate it: the measured rejections against the local copies were
`$.schemaVersion: '1.2' is not one of ['1.0', '1.1']` (FHP) and
`$.schemaVersion: '2.1' is not of type 'number'` (FHR, whose local copy is FHR
1.0). Validation was then done against the released contracts, two independent
ways, as recorded above.

That FHP-side gap closed with [#31](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/31):
this repository's working `fhp.json` is now the v0.6.0-released FHP 1.2 bytes,
and `tests/test_dmel_chr4_fixture.py` validates the header of
`chr4.fhp.fasta` against it through the repository's own test gate:

```text
$ python -m unittest tests.test_dmel_chr4_fixture -v  # (excerpt)
test_fhp_header_validates_against_working_fhp_json (tests.test_dmel_chr4_fixture.WorkingContractValidationTests) ... ok
Ran 13 tests in 0.431s
OK
```

Measured directly with `jsonschema` 4.26.0 (`Draft202012Validator` with
`FormatChecker`) against the working `fhp.json` (FHP 1.2): 0 errors. The
fixture stays in a subdirectory the flat example glob does not read, because
`metadata.fhr.yaml` is not FHP metadata and this tree's `fhr.json` remains the
frozen FHR 1.0 compatibility copy (Q2): the FHR header is still validated by
the released toolkit and the shared repository, not by this repository's
gates.

## Not verified

- **Back-translation.** `translatedFrom` states the relationship the annotation
  itself records (these CDS are features on `NC_004353.4`). Nobody re-translated
  the chr4 sequence and compared the products against these 298 records. The
  toolkit says the same thing in its own output ("A match confirms file identity
  only, not that the translations are correct").
- **Schema validation of the FHR header by this repository's own gates.** The
  FHP header is validated locally since #31 (see above); the FHR header is not,
  because this tree's `fhr.json` is the frozen FHR 1.0 compatibility copy.
- **Whether the FHT lane's chr4 parent is this same file.** chr4 was chosen so an
  FHP and an FHT fixture could share one parent. While this work was in progress
  the FHT lane opened
  [FHT-Specification#45](https://github.com/FAIR-bioHeaders/FHT-Specification/pull/45)
  with its own chr4 FHR. Compared by measurement, not by reading their prose:
  - the **sequence body is the same file's worth of bytes**. Their
    `pilot/dmel-chr4/provenance.json` records the sliced record as SHA-256
    `9ea85183fc77137381a6e81adf8f088c84c68a888dc323ef8b286b4ef165e184`, which is
    what `derive_chr4.py` produces here, and their per-chromosome cross-check file
    matches the one measured above (`chr4.fna.gz` SHA-256 `c0d89f2a…`,
    decompressed `bbaaf2ec…`). Their masking and gap figures — 374,633 lower-case
    ACGT characters, one 17,000-base `within_scaffold` gap at 1200663-1217662,
    GC 35.25 % — agree with this record independently of it.
  - the **headers differ, so the parent digests differ**. Their FHR digest is
    `qQs9oEKygk63F7ppYVl9te6U8lVHeE8Fbzlf7lmB4Yw=`, this one is
    `fHGkIi8u8lJCJstnJoQXM7XsXp/HXEyOe6y8GyGZO1k=`. Their field choices are not
    wrong, just different: `accessionID` names the molecule rather than the
    assembly, `version` carries the assembly name, `vitalStats` is filled, and no
    `reuseConditions` is asserted.
  - that difference doubled as an external check on this document's
    standard-library re-derivation: concatenating their published header block
    with the slice above reproduces their `qQs9oEKy…` value exactly.

  So the two lanes do **not** currently share one parent digest and this PR does
  not claim they do. Choosing one canonical chr4 FHR header — which repository
  hosts it, and whether `accessionID` names the assembly or the molecule — is a
  maintainer decision spanning both repositories. If the FHT form wins, the FHR
  file here and the `derivedFrom` digest in `metadata.fhp.yaml` have to be rebuilt
  and re-verified together, never patched in place.
- **Gene-level completeness of the protein set.** `isoformPolicy: all` describes
  this file relative to this delivery (every `protein_id` the GFF states on
  `NC_004353.4` is present, nothing filtered). Whether FlyBase Release 6.54
  publishes further isoforms somewhere else is not something these bytes can
  establish.
- **Biology beyond the records above**: no taxonomy depth, strain history,
  expression, function or homology claim is made or implied.
- **The delivery as it will look tomorrow.** NCBI refreshes "latest" assemblies;
  the digests above pin what was retrieved on 2026-11-15 and `derive_chr4.py`
  refuses mismatching inputs instead of continuing.

## Reproducing the pair

```sh
# 1. fetch the delivery — whole files, never ranged reads
B=https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/215/GCF_000001215.4_Release_6_plus_ISO1_MT
P=GCF_000001215.4_Release_6_plus_ISO1_MT
for f in md5checksums.txt uncompressed_checksums.txt \
         ${P}_assembly_report.txt ${P}_assembly_stats.txt ${P}_feature_count.txt \
         ${P}_feature_table.txt.gz ${P}_genomic.gbff.gz ${P}_genomic.fna.gz \
         ${P}_genomic.gff.gz ${P}_cds_from_genomic.fna.gz ${P}_protein.faa.gz; do
  curl -sS --fail -O "$B/$f"
done

# 2. derive and measure the sequence inputs; verifies the pinned digests first
python3 examples/fhp/dmel-chr4/derive_chr4.py --input-dir . --output-dir work

# 3. author the headers with the released toolkit, FHR first
python3 -m venv bh && ./bh/bin/pip install "fair-bioheaders==0.11.0"
./bh/bin/bioheaders combine --type fasta examples/fhp/dmel-chr4/metadata.fhr.yaml \
    work/chr4_genomic.fna  -o examples/fhp/dmel-chr4/chr4.fhr.fasta
./bh/bin/bioheaders convert --from fasta --to json examples/fhp/dmel-chr4/chr4.fhr.fasta -
#    put that checksum into derivedFrom of metadata.fhp.yaml, then:
./bh/bin/bioheaders combine --type fasta examples/fhp/dmel-chr4/metadata.fhp.yaml \
    work/chr4_proteins.faa -o examples/fhp/dmel-chr4/chr4.fhp.fasta

# 4. check
./bh/bin/bioheaders verify       examples/fhp/dmel-chr4/chr4.fhr.fasta
./bh/bin/bioheaders verify       examples/fhp/dmel-chr4/chr4.fhp.fasta
./bh/bin/bioheaders verify-links examples/fhp/dmel-chr4/chr4.fhp.fasta \
                                 examples/fhp/dmel-chr4/chr4.fhr.fasta
python3 -m unittest discover -s tests -p "test_dmel_chr4_fixture.py" -v
```

The metadata inputs are committed and the sequence inputs are reproducible from
the pinned digests, so step 3 must reproduce the committed bytes, and the test in
step 4 fails if the pair stops matching.
