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

This repository is **not an independent publication authority**. FHP model,
documentation and example work happens here on branches and publishes through
the shared repository by pull request (family migration:
[#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107),
establishment tracker:
[#158](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/158)).
The tree started as a copy of the family publication tree; what belongs here,
which files are pinned compatibility copies, and the canonical v0.5.0 pins are
classified in **[docs/DEVELOPMENT-TREE-PROPOSAL.md](docs/DEVELOPMENT-TREE-PROPOSAL.md)**
(issue [#2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2)).
Until the synchronization in issue
[#3](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/3) lands,
this root tree still carries the **FHP 1.0 line** (`fhp.json`,
`fhp_linkml.yml` importing the pinned `schemas/core-v0.4.yaml`) and the older
draft-era `docs/FHP.md`; the released v0.5.0 text is authoritative and lives
in the shared repository.

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
  the model imports the pinned shared core `schemas/core-v0.4.yaml` and
  `schemas/shared.yaml`.
- Required fields (FHP 1.0): `schema`, `schemaVersion`, `proteome`,
  `sourceType` (`predicted` | `database` | `mixed`), `taxon`, `version`,
  `metadataAuthor`, `dateCreated`, `checksum`. Field semantics and rules are
  in [docs/FHP.md](docs/FHP.md); examples — minimal and rich, for each of the
  three `sourceType` values — in [examples/fhp/](examples/fhp/), conformance
  vectors in [conformance/](conformance/README.md).
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
python scripts/make_jsonld.py --check
python scripts/check_conformance.py
```

For an intentional model change, regenerate `fhp.json` with the command above,
review the schema diff, and update the drift baseline only with explicit
maintainer review (`python scripts/check_schema_drift.py --schema fhp.json
--baseline .github/schema-baseline-fhp.json --update`). CI workflows also run
the inherited FHR/FHGFF3 family checks; their scope in this repository is a
decision recorded in the development-tree proposal (issue #3).

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
v0.5.0 for FHP 1.1).

**Historical issue numbers:** before 2026-10-14 this tree lived in the
repository then named `FHR-Specification`; `#N` references inherited from that
era (for example in `specs/` and `docs/`) resolve to
[FAIR-bioHeaders-Specification](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues),
not to this repository's own issues ([#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107)).

## Licensing

[![License: MPL-2.0](https://img.shields.io/badge/License-MPL--2.0-blue.svg)](LICENSE)

New project contributions from March 2025 onward use [MPL-2.0](LICENSE). David Molik left USDA in February 2025. Historical USDA public-domain material remains public domain within the United States; its original notice is preserved in LICENSE. Previously granted permissions and third-party terms remain intact. The project includes both historical material and subsequent MPL-2.0 contributions; file notices and history identify provenance.
