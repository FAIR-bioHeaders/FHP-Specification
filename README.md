# FHP-Specification (FHP development)

[![Specification checks](https://github.com/FAIR-bioHeaders/FHP-Specification/actions/workflows/validate-specification.yml/badge.svg?branch=main)](https://github.com/FAIR-bioHeaders/FHP-Specification/actions/workflows/validate-specification.yml)
[![Schema drift checks](https://github.com/FAIR-bioHeaders/FHP-Specification/actions/workflows/check-schema-drift.yml/badge.svg?branch=main)](https://github.com/FAIR-bioHeaders/FHP-Specification/actions/workflows/check-schema-drift.yml)

**This repository is the development home of FHP — the FAIR-bioHeaders header
for protein FASTA** (proteomes and protein sets: predicted, database and mixed
origins). FHP is a small YAML block embedded in `;~` comment lines at the top
of a protein FASTA file, validated against a JSON Schema contract and covered
by a SHA-512/256 checksum of the file's exact bytes.

## Released contract versus development repository

The **published FHP specification lives in
[FAIR-bioHeaders-Specification](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification)**
(called `FHR-Specification` until 2026-10-14,
[#108](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/108))
and is cited by versioned URLs — never invent one:

| FHP `schemaVersion` | Released in | Persistent schema URL |
| --- | --- | --- |
| `"1.0"` | FAIR-bioHeaders-Specification v0.4.0–v0.4.2 | <https://w3id.org/fair-bioheaders/fhp/v0.4.0> |
| `"1.1"` (optional `x-` extension fields) | FAIR-bioHeaders-Specification v0.5.0 | <https://w3id.org/fair-bioheaders/fhp/v0.5.0> |
| `"1.2"` (dotted BUSCO dataset versions) | FAIR-bioHeaders-Specification v0.6.0 | <https://w3id.org/fair-bioheaders/fhp/v0.6.0> |

This repository is **not an independent publication authority**. FHP model,
documentation and example work happens here on branches and publishes through
the shared repository by pull request (family migration:
[#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107),
establishment tracker:
[#158](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/158)).
The tree started as a copy of the family publication tree; what belongs here,
which files are pinned compatibility copies, and the canonical pins are
classified in **[docs/DEVELOPMENT-TREE.md](docs/DEVELOPMENT-TREE.md)**
(adopted from
[docs/DEVELOPMENT-TREE-PROPOSAL.md](docs/DEVELOPMENT-TREE-PROPOSAL.md);
issue [#2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2)).
The synchronization in issue
[#3](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/3) has
landed, and issue
[#31](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/31) re-pinned
the **FHP contract chain** — `fhp.json` (generated from `fhp_linkml.yml`, which
imports the vendored `schemas/core-v0.5.yaml` and `schemas/shared-v0.6.yaml`
snapshots), `schemas/versions.json` and the
`tests/fixtures/releases/fhp-v0.6.0.json` release pin — to the shared **v0.6.0**
release commit (FHP `1.2`). The regenerated `fhp.json` is byte-identical to the
released `v0.6.0/fhp.json`. Everything else that issue #3 synced —
`docs/FHP.md`, `docs/SCHEMA-VERSIONS.md`, the shared `examples/fhp/` files and
the byte-unchanged `fhp-fasta` vectors — stays byte-pinned to the shared v0.5.0
release commit, and all of it is verified against `provenance.json` by
`scripts/check_shared_parity.py` in CI. The conformance
package was wired as **FHP-owned** under the Q4 decision
([issue #2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2),
2026-11-12): `conformance/manifest.json` covers the complete v0.5.0
`fhp-fasta` vector set — byte-pinned to the shared release commit, the former
deferred additions included — plus this repository's own
`fhp-fasta-author-bad-name-type` and the shared FASTA-container vectors that
exercise the `docs/FORMAT.md` rules on the same FASTA header reader. The
complete family manifest is not maintained here; it runs from the pinned
shared tree under `.github/workflows/shared-parity.yml`.

**Canonical here:** this repository is the current raw-`main` source of the FHP
JSON-LD context and vocabulary (`jsonld/fhp.context.jsonld`,
`jsonld/fhp.terms.jsonld`, `jsonld/fhp.terms.ttl`), and of the FHP HTML-microdata
binding ([docs/FHP-MICRODATA.md](docs/FHP-MICRODATA.md)); the
[FAIR-bioHeaders-Tools](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools)
serializers resolve the FHP context from the raw-main path. The current Pages
build publishes the vocabulary and FHR/family JSON-LD files, not FHP files or
FHP versioned aliases; those Pages surfaces remain pending work.

## Working with FHP

- The contract: `fhp.json` (generated — never hand-edited) from
  `fhp_linkml.yml` with
  `python json-schema-generator.py --type fhp --output fhp.json`;
  the model imports the pinned shared core `schemas/core-v0.5.yaml` and
  the v0.6.0 shared object-model snapshot `schemas/shared-v0.6.yaml`
  (#31; the plain `schemas/shared.yaml` stays at v0.5.0 for the frozen
  FHGFF3 compatibility copy).
- Required fields (FHP 1.0, 1.1 and 1.2 — 1.1 adds only optional `x-` extension
  fields, 1.2 only widens the BUSCO `lineageDataset` pattern): `schema`,
  `schemaVersion`, `proteome`,
  `sourceType` (`predicted` | `database` | `mixed`), `taxon`, `version`,
  `metadataAuthor`, `dateCreated`, `checksum`. Field semantics and rules are
  in [docs/FHP.md](docs/FHP.md); examples — minimal and rich, for each of the
  three `sourceType` values — in [examples/fhp/](examples/fhp/), conformance
  vectors in [conformance/](conformance/README.md). The one real-data pair,
  [examples/fhp/dmel-chr4/](examples/fhp/dmel-chr4/README.md), is a
  chromosome 4 subset of *Drosophila melanogaster* `GCF_000001215.4` (FHR 2.1
  parent plus FHP 1.2 child, headers written by the released toolkit); its
  README records the source digests, the selection rule and the measurements,
  and it is a pilot/teaching artifact rather than a production reference or a
  conformance vector.
- **Version pin.** This tree's FHP contract chain is pinned to the shared
  v0.6.0 release (FHP `1.2`, #31); the shared docs, examples and vectors are
  still pinned at v0.5.0, and the frozen legacy FHR copy is FHR `1.0`. So
  `scripts/validate_examples.py`, `scripts/check_conformance.py --schema` and
  the unit suite here validate 1.0/1.1/1.2 instances against the released
  bytes. The `examples/fhp/dmel-chr4/` fixture targets the released contracts;
  its FHP header now validates against this repository's own working
  `fhp.json` (`tests/test_dmel_chr4_fixture.py`), while its FHR header remains
  outside this tree's gates (frozen FHR 1.0 copy) and is validated by the
  released toolkit, as that fixture's README records.
- **Use the toolkit, not a converter in this repository.**
  [FAIR-bioHeaders-Tools](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools)
  (`pip install fair-bioheaders`) is the single active family toolkit:
  `bioheaders combine`, `verify` and `strip` handle FHP headers and checksums.
  Never write or edit a checksum by hand. No FHP-specific converter will be
  created here; the archived FHT-File-Converter is not an active dependency.
- Strict FASTA readers (samtools faidx and the rest of htslib, Picard,
  Biopython's default `fasta` format) reject a leading `;~` block; see
  [docs/TOOL_COMPATIBILITY.md](docs/TOOL_COMPATIBILITY.md).
- Scientific care for protein sets: asserted source provenance is not a
  QC result; do not infer a genome parent, genetic code, isoform policy,
  database release or BUSCO counts from the presence of protein sequences,
  and never invent identifiers, authors or provenance.

## Checks in this checkout

Python 3.13 or later; `python -m pip install -r requirements-linkml.txt`
(plus `requirements-jsonld.txt` for the JSON-LD tests).

```bash
python -m unittest discover -s tests -v
python scripts/validate_examples.py --schema fhp.json --examples examples/fhp
python scripts/check_linkml.py
python scripts/check_schema_drift.py --schema fhp.json --baseline .github/schema-baseline-fhp.json
python scripts/make_jsonld.py --check --fhp
python scripts/check_conformance.py
python scripts/check_shared_parity.py
```

For an intentional model change, regenerate `fhp.json` with the command above,
review the schema diff, and update the drift baseline only with explicit
maintainer review (`python scripts/check_schema_drift.py --schema fhp.json
--baseline .github/schema-baseline-fhp.json --update`). Under the Q2 decision
(2026-11-12, [docs/DEVELOPMENT-TREE.md](docs/DEVELOPMENT-TREE.md)) CI generates
and drift-checks **FHP only**: the inherited FHR/FHGFF3 contracts, models and
their generated outputs are pinned compatibility fixtures whose bytes are
asserted by `scripts/check_shared_parity.py` against the `pinned` section of
`provenance.json`.

## Project guidance

See [CONTRIBUTING](CONTRIBUTING.md), [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md),
[SECURITY](SECURITY.md), and [AGENTS](AGENTS.md). David and Adam retain
schema and release authority;
[GOVERNANCE](GOVERNANCE.md) describes the current two-maintainer model and a
future steering-group option that is not active.
[Release notes](CHANGELOG.md) document compatibility and deferred work.
[Diagram.svg](Diagram.svg) is the inherited FHR schema diagram from the
family tree, kept as provenance pending the FHP-specific diagram decision
(issue #2).

## Citing

FHP metadata work is motivated by the published FHR paper:

> Wright, Adam, Mark D. Wilkinson, Christopher Mungall, Scott Cain, Stephen
> Richards, Paul Sternberg, Ellen Provin, Jonathan L. Jacobs, Scott Geib,
> Daniela Raciti, Karen Yook, Lincoln Stein, and David C. Molik. “FAIR Header
> Reference Genome: A TRUSTworthy Standard.” *Briefings in Bioinformatics* 25,
> no. 3 (2024): bbae122. https://doi.org/10.1093/bib/bbae122.

The Zenodo records in `CITATION.cff` belong to the **FHR specification and
converter** resources — they are related family history, not FHP identifiers,
and no FHP DOI is implied by them. The
publication and DOI identity of *this* repository is tracked in issue
[#6](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/6) and
coordinated with
[FHR-Citation](https://github.com/FAIR-bioHeaders/FHR-Citation/blob/main/citation.bib);
until that lands, cite the released FHP contract as the
FAIR-bioHeaders-Specification release carrying it (v0.4.0–v0.4.2 for FHP 1.0,
v0.5.0 for FHP 1.1, v0.6.0 for FHP 1.2).

**Historical issue numbers:** before 2026-10-14 this tree lived in the
repository then named `FHR-Specification`; `#N` references inherited from that
era (for example in `specs/` and `docs/`) resolve to
[FAIR-bioHeaders-Specification](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues),
not to this repository's own issues ([#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107)).

## Licensing

[![License: MPL-2.0](https://img.shields.io/badge/License-MPL--2.0-blue.svg)](LICENSE)

New project contributions from March 2025 onward use [MPL-2.0](LICENSE). David Molik left USDA in February 2025. Historical USDA public-domain material remains public domain within the United States; its original notice is preserved in LICENSE. Previously granted permissions and third-party terms remain intact. The project includes both historical material and subsequent MPL-2.0 contributions; file notices and history identify provenance.
