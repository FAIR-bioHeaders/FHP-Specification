# FHP and PSI PEFF: scope, crosswalk and placement study

This study answers [FHP-Specification #20](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/20).
It evaluates the released FHP 1.2 contract and PEFF 1.0, without changing either
contract. The reproducible synthetic probes and captured diagnostics are in
[`studies/peff/`](../studies/peff/README.md).

## 1. Placement: keep conforming serializations separate

**There is no standards-conforming shared placement of a literal FHP `;~` block
and a PEFF 1.0 file header under the current rules.** PEFF §3.3.1 requires the
first file line to identify PEFF and all file-header lines to begin with `# `.
FHP uses `;~` YAML lines before the first FASTA record (FORMAT R10). Putting FHP
first violates PEFF's first-line requirement. Putting it after the PEFF block,
or between PEFF header sections, leaves non-PEFF lines before the first record.
Changing FHP to `# key=value`, embedding YAML as a PEFF GeneralComment, or
prefixing the whole FHP block with `# ` would define a different serialization;
none is an adopted coexistence syntax.

Measured on 2026-11-16, using the versions pinned below:

| Placement/control | Pyteomics 5.0 IndexedPEFF | PSI downloadable validator | Comet PEFF-mode indexing | bioheaders 0.11.0 |
| --- | --- | --- | --- | --- |
| PEFF only | 2 proteins, database metadata retained | valid | 10 peptides | no FHP header |
| FHP only | rejected as PEFF | not recognized | same 10 peptides | valid |
| FHP before PEFF | rejected as PEFF | not recognized | same 10 peptides | valid |
| PEFF then FHP then records | 2 proteins, database metadata retained | invalid: 15 IllegalPEFFLine errors | same 10 peptides | valid |
| PEFF first line, FHP, remaining PEFF header | 2 proteins, **database metadata lost** | invalid: 15 IllegalPEFFLine errors | same 10 peptides | valid |
| PEFF missing Prefix | 2 proteins; incomplete metadata accepted | invalid: 4 errors | same 10 peptides | no FHP header |
| PEFF wrong NumberOfEntries | 2 proteins; erroneous count accepted | invalid: 1 error | same 10 peptides | no FHP header |
| Plain FASTA | rejected as PEFF | not recognized | same 10 peptides | no FHP header |
| FHP with a changed residue and stale checksum | rejected as PEFF | not recognized | different peptide table | checksum failure |

“Not recognized” is the Perl tool's `status=NOTSET`, exit 5, without an
`isValid` result. Its exit status alone is insufficient: recognized **invalid**
files return exit 0 with `isValid=0`. The positive PEFF control returns
`isValid=1`, zero validation errors/warnings, and two entries. Pyteomics is a
reader, not a full PEFF validator: its success on the two invalid PEFF controls
makes that distinction measurable. Its inside-header result is particularly
unsafe because returning protein sequences conceals lost database provenance.

Comet 2026.03 rev. 1 was built from the pinned source and run with
`peff_format=1`, the pinned PSI-MOD ontology, and peptide-index creation (`-j`).
The harness reads its v5 index raw peptide table and compares sequences,
flanks, masses and modification filters; matching an exit code or peptide count
alone is insufficient. These are indexing results for two unmodified synthetic
proteins, **not** a mass-spectrometry search, modification/variant coverage,
PEFF-header validation, or evidence that every Comet version accepts a hybrid.
The downloadable validator snapshot predates the final 2019 document; its
observations are reported separately from the final specification requirements.
No file was submitted to the online validator.

For a PEFF consumer, supply a conforming PEFF file. For an FHP consumer, supply
an FHP FASTA serialization. Keep protein record bytes identical when making
those two representations and retain explicit provenance of their relationship.
The full-file FHP checksum includes the surrounding header bytes (apart from
its scalar checksum line), so two representations need their own computed
checksums; equal proteins do not imply equal file checksums. An FHP sidecar can
describe a PEFF resource only under a separately specified, verified binding;
this study introduces no sidecar binding, automatic stripping command, converter,
or new schema fields. A future common encoding would need agreement with PSI
and new interoperability evidence.

## 2. Crosswalk and information loss

A PEFF file can contain multiple database-description blocks. FHP describes one
protein **set**, including subsets or mixtures. A database field cannot be
filled from the first source record simply because a similarly named FHP slot
exists. The table covers all 25 named FHP 1.2 root properties; extension fields
need their own explicit mapping and loss report.

| FHP property/group | PEFF candidate | Conditions and loss |
| --- | --- | --- |
| `proteome` | `DbName` | Conditional set/database label correspondence; split a mixture into identified databases or retain a set-level description externally. |
| `source[].name`, `.release`, `.url`, `.setIdentifier`; `sourceType` | `DbName`, `DbVersion`, `DbSource` | Source provenance is not necessarily the distributed database identity. Preserve all source records and sourceType; no one-to-one flattening. A missing URL must not be invented. Source assemblyAccession, description and sequenceCount have no exact PEFF database-header counterpart; retain them separately. |
| `version` | `DbVersion` | Only when the FHP set and PEFF database have the same versioned identity; subset/run versions can differ from upstream releases. |
| `sequenceStats` | `NumberOfEntries` | Only the record count corresponds. Compute it from the actual exported records; retain other statistics separately. Asserted FHP statistics are not proof of output counts. |
| `taxon` | Per-entry `TaxName` / `NcbiTaxId` | Set taxonomy is not evidence for each entry in mixed sets. Identifiers must be translated with an explicit namespace rule; do not copy a taxonomy URI verbatim into a numeric NcbiTaxId. |
| `accessionID`, `identifier` | No general exact equivalent | These identify the set; `DbUniqueId` identifies an entry within `Prefix`. Never assign a set accession to every protein. |
| `isoformPolicy` | No exact equivalent | PEFF entry variants/proteoforms do not state a set's isoform selection policy. |
| `geneticCode`, `predictionProtocol`, `predictionSoftware` | No exact standard field correspondence | Translation/annotation provenance must survive separately; do not turn software versions into DbVersion. |
| `completeness` | No exact equivalent | Preserve BUSCO counts, lineage and version together. NumberOfEntries is not completeness. |
| `checksum`, `derivedFrom` | No equivalent FHP byte-identity contract | Retain SHA-512/256 and parent checksum relationships in their own typed form; PEFF identifiers cannot substitute for them. Recompute after serialization changes. |
| `schema`, `schemaVersion` | No equivalent | FHP contract selectors differ from the PEFF format-version line. |
| `metadataAuthor`, `dateCreated` | No exact equivalent | Metadata authorship/date is not automatically the database producer, source or release date. |
| `documentation`, `scholarlyArticle`, `relatedLink` | `GeneralComment` as human-readable fallback only | Flattening loses typed URL/citation roles and structure; it is not a reversible field mapping. |
| `funding`, `reuseConditions`, `voucherSpecimen` | No exact equivalent | Preserve grant, provenance-era reuse terms and specimen structure externally; a free-text comment does not retain machine semantics. |

Conversely, PEFF requires `Prefix`, `NumberOfEntries` and `SequenceType`, plus
`DbName`, `DbSource` and `DbVersion` in each database block. FHP has no `Prefix`
slot. A producer must choose a valid database namespace and preserve stable
entry IDs; neither taxon nor proteome name determines it. `SequenceType=AA`
comes from a known protein export, not a guess from metadata (PEFF also supports
nucleotide sequences). PEFF's sequence-header annotations for modifications,
variants, processing and proteoforms have no lossless FHP-header destination.
Keep the original PEFF records; converting only database metadata cannot retain
them. PEFF §3.4 controlled-vocabulary rules also prevent treating arbitrary FHP
keys or `x-` extensions as automatically legal PEFF keys.

A future exporter could support the conditional subset above, provided it
requires explicit database/entry identity decisions, validates required PEFF
fields, preserves protein bytes and annotations, computes each representation's
checksum, and emits a machine-readable loss report for every unmapped field.
**No such converter is implemented or claimed by this study.**

## 3. Which format to use

Use PEFF when proteomics readers need database identity and structured per-entry
sequence annotations, including proteoforms and modifications. Use FHP when a
protein set needs file-bound discovery/provenance, source and prediction history,
isoform selection, BUSCO completeness, reuse terms, and byte-level identity or
parent links across the FAIR BioHeaders family. Their scopes overlap in database
labels and releases, but neither subsumes the other. A workflow needing both
should retain separately validated representations and their transformation
provenance rather than assume concatenating headers creates an interoperable
file. PEFF is not limited to protein FASTA, while FHP is specifically a
protein-set metadata contract.

## 4. Why semicolon-prefixed YAML

The semicolon is the comment convention of Pearson FASTA; Biopython's
`FastaPearsonIterator` explicitly supports it. It keeps small file-level metadata
out of record identifiers, while YAML provides a readable nested representation
for sources, authors, taxon, completeness and parent relationships shared with
the family's JSON/JSON-LD representations. PEFF instead establishes its own
`# ` file-header grammar and controlled `\key=value` entry grammar for its
database/sequence-annotation purpose. Replacing FHP YAML with that grammar would
require a new serialization and rules for nested values and typing.

This is a design rationale, not a claim that every FASTA reader implements
Pearson comments. FORMAT R11 avoids raw `>` and `@` in written metadata values
by YAML double-quoted escapes `\x3E` and `\x40`; otherwise several readers can
mistake metadata for a record. Decoding restores the original values. R12
requires YAML 1.2 core-schema values that also read consistently under YAML 1.1,
rejects explicit tags and ambiguous unquoted scalars, and requires writers to
quote ambiguous strings. These constraints address concrete FASTA and YAML
interoperability risks; they do not make `;~` legal in PEFF.

## Primary sources and pins

- [HUPO-PSI PEFF](https://www.psidev.info/peff), ratified PEFF 1.0 specification:
  [final PDF at pinned commit](https://github.com/HUPO-PSI/PEFF/blob/4b41d2697f3e85e9ca9d93fdc6934735546c33f3/Specification/PEFF_SpecDoc_1.0_FINAL.pdf),
  §3.3–3.4; April 5, 2019. PDF SHA-256 is in the study manifest.
- [Primary PEFF paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6642660/), 2019.
- [Pyteomics PEFF API](https://pyteomics.readthedocs.io/en/latest/api/peff.html),
  measured installed package 5.0; installed source digests are recorded.
- [Comet pinned source](https://github.com/UWPR/Comet/tree/c990672cfd1aebb5b65a475731a0f4790dff5c77),
  especially `CometSearch/CometSearch.cpp` and `CometPeptideIndex.cpp`.
- [PSI-linked Perl validator archive](https://peptideatlas.org/export/PEFF/ProteomicsPEFF.zip),
  downloaded 2026-11-16; archive entries dated 2018. The archive provides no
  declared package version, so its SHA-256 identifies the measured snapshot.
- [Biopython Pearson parser](https://biopython.org/docs/latest/api/Bio.SeqIO.FastaIO.html#Bio.SeqIO.FastaIO.FastaPearsonIterator).
- [FHP published contract v0.6.0](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/blob/v0.6.0/fhp.json)
  and [shared FORMAT rules](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/blob/v0.6.0/docs/FORMAT.md).
