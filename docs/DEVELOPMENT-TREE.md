# The FHP development tree

This repository, `FAIR-bioHeaders/FHP-Specification`, is the **development home
for FHP — the FAIR-bioHeaders header for protein FASTA**. The released
specification for every FAIR-bioHeaders type, including FHP, is published from
`FAIR-bioHeaders/FAIR-bioHeaders-Specification` (called `FHR-Specification`
until 2026-10-14). This document is the adopted, current classification of the
tree: what belongs here, what is a byte-pinned shared copy, and what is frozen
inherited family state.

It condenses the merged proposal
[DEVELOPMENT-TREE-PROPOSAL.md](DEVELOPMENT-TREE-PROPOSAL.md)
([#21](https://github.com/FAIR-bioHeaders/FHP-Specification/pull/21),
issue [#2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2))
after the bounded issue-#3 synchronization
([#23](https://github.com/FAIR-bioHeaders/FHP-Specification/pull/23), commit
`cc0334b`) and the 2026-11-12 maintainer decisions on the open questions — the
Q2 freeze and the Q4 FHP-owned conformance package, implemented in this tree
below. The proposal file stays in place unchanged as the 2026-11-10 audit
record — its path is cited by the digest-pinned provenance header of
`schemas/core-v0.5.yaml` and by `provenance.json` records, so it is superseded
in status, not moved or deleted.

Family migration tracker: [FAIR-bioHeaders-Specification#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107).
Establishment tracker:
[FAIR-bioHeaders-Specification#158](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/158).

## Canonical ownership

- The **published FHP metadata contract** is `fhp.json` in
  FAIR-bioHeaders-Specification at each release tag (w3id URLs:
  `https://w3id.org/fair-bioheaders/fhp/v0.4.0` for FHP 1.0,
  `.../v0.5.0` for FHP 1.1). It is never edited here; this repository's root
  `fhp.json` is the pinned v0.5.0 compatibility copy, regenerated only from
  the shared bytes.
- The **FHP LinkML model** develops in this repository on branches
  (`fhp_linkml.yml`), publishes through the shared repository by pull request,
  and the shared published copy is then synced back. On `main` it is now the
  synchronized v0.5.0 (FHP 1.1) copy, subject to parity, not a free local file.
- The **FHP JSON-LD context/vocabulary, the microdata binding and their
  fixtures** (`jsonld/fhp.*`, [FHP-MICRODATA.md](FHP-MICRODATA.md),
  `examples/fhp/*.fhp.jsonld` and `*.microdata.fhp.html`, the FHP readers in
  `tests/`) are owned and published **here** — this repository's raw `main` is
  their canonical source and the toolkit resolves the FHP context from it.
  They are FHP development outputs, not byte-copies of shared files.
- **Shared core/imports** (`schemas/*`, `docs/FORMAT.md`,
  `docs/SCHEMA-VERSIONS.md`, the `fhp-fasta` vectors and the other
  digest-pinned shared copies) are published by the shared repository.
  Local files listed in `provenance.json`'s `copied[]` are
  digest-verified pinned copies. Files listed under `pinned` are inherited
  FHR/FHGFF3 artifacts frozen at their historical shared commit
  (Q2, implemented 2026-11-12); files listed only under `legacy` are the
  remaining frozen pre-v0.5.0 family state. Neither group is a
  generation target here, and both are byte-verified rather than
  hand-editable. The one exception is `conformance/manifest.json`: since
  Q4 it is generated here as the FHP-owned manifest (below), not a
  shared copy.
- The **active converter/validator** is FAIR-bioHeaders-Tools
  (`pip install fair-bioheaders`); the FHP JSON-LD and typed-HTML reader and
  writer shipped there in **0.8.2** (Tools
  [#98](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools/pull/98),
  closing [#58](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools/issues/58)).
  No FHP-specific converter lives in this repository.

## Development branches versus released `main`

- Develop FHP model, documentation and example work on branches; reviewed
  schema changes publish in FAIR-bioHeaders-Specification first, then this
  `main` is synchronized from the published bytes.
- Do not make an independent schema change on `main` that diverges the pinned
  copies from their recorded upstream commits; the parity check fails first.
- Never rewrite history, tags or released bytes. The immutable released-FHP
  pins (`tests/fixtures/fhp/v0.4.0/`, `tests/fixtures/releases/`) keep the
  1.0 line testable; historical fixtures are replaced only by additions.
- Published paths served by consumers (`jsonld/fhp.context.jsonld` and the
  other raw-`main` FHP surfaces) may not be deleted or moved without a
  coordinated toolkit change. GitHub Pages for FHP files and versioned FHP
  aliases remain pending publication work; do not claim them as live.

## Enforcement point

`provenance.json` (repository root) is the machine-readable truth of the pin:
source commit `170e677fbb6726a3f765373dbe1f214820000be7` (shared tag
`v0.5.0`), the `copied[]` digests with two machine-checkable adjustments
(`fhp_linkml.yml` import retarget to `schemas/core-v0.5`; the provenance
header on the vendored `schemas/core-v0.5.yaml`), the per-entry companion pin
of `examples/fhp/rich-predicted.fhp.yaml` to `e1e5998` (shared #201), the
`legacy` freeze, the `owned` classification and the `strictDirs` rule that an
unclassified new path under `schemas/`, `conformance/valid/`,
`conformance/invalid/` or `examples/fhp/` fails the check.

Exactly one script enforces the bytes: `scripts/check_shared_parity.py`
(digest-only offline; `--upstream PATH` against a shared checkout), wired in
`.github/workflows/shared-parity.yml`. It verifies the `copied[]` digests,
the `pinned` compatibility artifacts against their recorded historical
digests (so silent drift of a frozen FHR/FHGFF3 file fails CI), the
`imports` records and the `strictDirs` classification. That workflow
additionally requires
`copied[]` to equal exactly what `scripts/make_provenance.py` regenerates from
the pinned commit plus its hard-wired companion set — so a copy changes only
as part of a deliberate, generator-reproducible resync, never as a hand edit
or an isolated digest bump. There is no `check_development_tree.py` here
(FHR-Specification's counterpart): the Q7 decision (2026-11-12) keeps this
pair — `provenance.json` + `scripts/check_shared_parity.py` +
`shared-parity.yml` — as **the** enforcement point, with the classification
living in this document.

## Post-sync re-pin task (live drift)

The shared repository corrected the F-01 serialization bullet in
`docs/FHP.md` after the v0.5.0 tag (shared PR #218, commit `29034bf`), so
this repository's digest-pinned `docs/FHP.md` is the v0.5.0 text while shared
`origin/main` carries the corrected text. It must not be hand-edited (parity)
and must not be re-pinned in isolation (the regeneration step above, plus
`tests/test_make_provenance.py`, tie `copied[]` to the generator's
release-commit output and the single companion file). The correction arrives
with the next deliberate resync to a shared release that includes it: re-copy
bytes + `scripts/make_provenance.py` + `provenance.json` update in one PR.
Recorded in `provenance.json` → `liveMain`. [JSONLD.md](JSONLD.md#fhp-draft)
notes the same divergence where local FHP text references `docs/FHP.md`.

## FHP-owned conformance package (Q4, implemented)

The Q4 decision ([#2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2),
maintainer comment of 2026-11-12): *FHP-owned vector subset + pinned-upstream
full run*. One manifest per purpose:

- `conformance/manifest.json` is FHP-owned, generated by
  `scripts/make_conformance.py`. It covers **every v0.5.0 `fhp-fasta` vector**
  — the 22 already byte-pinned at the issue-#3 sync, the 8 additions the v0.5.0
  manifest made (R15 extension fields, R11 escaped record markers, V1/V2/V4
  schema selection) and the `fhp-fasta-rich` byte update — verified
  byte-for-byte against the pinned shared tree (31 files: 13 valid, 18
  invalid), plus this repository's own `fhp-fasta-author-bad-name-type`
  vector (FHP-owned local addition, invalid, P1) and the shared
  **FASTA-container** vectors (45: 18 valid, 27 invalid) — the R-rule vectors
  the previous local run already executed through the same
  `fhr-fasta-validate` FASTA header reader, keeping the runnable set honest.
  77 vectors in total; `scripts/check_conformance.py --require-format
  fhp-fasta` runs them against the pinned `fair-bioheaders==0.9.0`, and the
  R15/V vectors pass (they shipped with that toolkit release).
- Rules the FHP-owned vectors do not exercise in both directions
  (microdata M1–M4, JSON-LD J1–J8, FHGFF3 G1–G3, R9, R12–R14, V3, V5, V6 and
  the valid-only R11/V1/V2) stay listed for the doc-token parity and carry
  explicit `notApplicable` notes pointing at the family manifest.
- The **complete family manifest** (GFA, microdata, JSON-LD, FHGFF3 vectors,
  40 rules) is *not* maintained here. It runs, unchanged and in full, from
  the pinned shared tree in the `shared-conformance` job of
  `.github/workflows/shared-parity.yml`, against the same toolkit release.
  The remaining pre-v0.5.0 family vector files stay on disk under
  `provenance.json` `legacy` as frozen history; the local regeneration check
  is scoped to the FASTA-container files the FHP-owned generator produces.
- `docs/FORMAT.md` moved into `copied[]` with the package: the FHP-owned
  vocabulary needs its v0.5.0 `[R11]`–`[R15]` tokens, and its bytes are
  byte-identical between the pin and current shared `main`. `docs/JSONLD.md`,
  `docs/MICRODATA.md` and `docs/FHGFF3.md` remain frozen pre-v0.5.0 copies
  (Q2): their v0.5.0 successors (`[J9]`, `[M5]`, the G1 grammar) are exercised
  by the family manifest upstream.

`provenance.json`'s `deferred` section resolved with this package and is
gone; the vector entries it recorded now carry digests in `copied[]`.

## Inherited FHR/FHGFF3 generation (Q2, implemented: frozen)

The Q2 decision (2026-11-12): **freeze**. FHP CI tests the FHP chain only:

- `validate-specification.yml` validates `fhp.json` and `examples/fhp/`,
  runs the FHP-only `scripts/check_linkml.py` and
  `scripts/make_jsonld.py --check --fhp`; `check-schema-drift.yml`
  drift-checks only `.github/schema-baseline-fhp.json`. The FHR and FHGFF3
  example-validation, equivalence, vocabulary and drift steps retired.
- The inherited chain — `fhr.json`, `fhr_linkml.yml`, `fhgff3.json`,
  `fhgff3_linkml.yml`, root `schemas/core.yaml` (v0.3-era, kept frozen for
  these fixtures only; FHP 1.1 builds solely on `schemas/core-v0.5.yaml`),
  the Pages-era `jsonld/fhr.context.jsonld`, `jsonld/terms.jsonld`,
  `jsonld/terms.ttl`, the generated `docs/TERMS.md`/`docs/MAPPINGS.md`, the
  FHR example serializations and the schema.org export expectations — is
  recorded in `provenance.json`'s `pinned` section: 24 files with local
  digests and their historical source commit `43f9067d0ce21e9ae63fd9eee64f9c2af0b73ff4`
  (shared `v0.4.0~1`, the inherited fork state of 2026-10-14).
  `scripts/check_shared_parity.py` verifies those bytes offline and against
  the recorded commit, so silent drift fails CI. No file was deleted: the
  preservation rule holds; retirement is of *CI generation targets*, not of
  files.
- The unit suite keeps the frozen fixtures honest as *content*:
  `tests/test_linkml.py`, `tests/test_core_schema.py` and
  `tests/test_fhgff3_schema.py` still check the frozen models'
  validation equivalence, and `make_jsonld.py --check` (unflagged) remains
  available locally. `json-schema-generator.py`'s legacy FHR/FHGFF3 paths
  stay exactly as the pre-v0.5.0 shared generator wrote them — restoring
  them to the shared `apply_fhr_rules()`/`apply_fhgff3_rules()` behavior
  would *diverge* the frozen contracts and is not part of Q2.

## Open questions (maintainer decisions)

All questions are now answered by the maintainer decisions of 2026-11-12
([#2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2),
"maintainer decisions recorded"); the Q2 and Q4 answers were implemented in
this tree on 2026-11-12 (commits "Wire the FHP-owned conformance package per
Q4. Refs #3" and "Freeze inherited generation per Q2. Refs #2"). Resolved in
implementation (recorded here for the audit trail):

- **Q1** — the shared-parity workflow pins
  `fair-bioheaders[jsonld]==0.9.0`, the first verified release that bundles
  the v0.5.0 schemas (0.8.2 bundles FHP only through v0.4.1).
- **Q2 — decided 2026-11-12: FREEZE; implemented.** FHP CI generates and
  drift-checks `fhp` only; the inherited FHR/FHGFF3 artifacts are `pinned`
  compatibility fixtures in `provenance.json`, byte-verified by
  `scripts/check_shared_parity.py` (see "Inherited FHR/FHGFF3 generation"
  above). No files deleted.
- **Q3** — the 1.1 model imports the vendored `schemas/core-v0.5.yaml` pin
  with the machine-checkable import retarget; the v0.3-era root core stays
  intact for the pinned compatibility chain, per Q2.
- **Q4 — decided 2026-11-12: FHP-owned vector subset + pinned-upstream full
  run; implemented.** See "FHP-owned conformance package" above.
- **Q5** — `CITATION.cff` carries the FHP development identity
  ([#22](https://github.com/FAIR-bioHeaders/FHP-Specification/pull/22),
  commit `c39199a`); FHR records are labeled related history, no FHP DOI is
  claimed.
- **Q7 — decided 2026-11-12: KEEP CURRENT.** `provenance.json` +
  `scripts/check_shared_parity.py` + `shared-parity.yml` is the enforcement
  point; no port of FHR's `check_development_tree.py`. The paragraph above
  ("Enforcement point") describes exactly what enforces; this document owns
  the classification.

Open, not a gate:

- **Q6 — decided 2026-11-12: DEFER.** No FHP-specific diagram is required for
  closure; `Diagram.svg` remains the inherited FHR schema diagram, kept as
  clearly labelled lineage/provenance until anyone wants a replacement via
  `scripts/render_diagram.py`.

## Working references

- The proposal's §2 inventory, §3 pin table and §8 audit commands remain the
  detailed 2026-11-10 record
  ([DEVELOPMENT-TREE-PROPOSAL.md](DEVELOPMENT-TREE-PROPOSAL.md)).
- Per-file classification for every path in this tree: `provenance.json`
  (`copied` / `imports` / `pinned` / `legacy` / `owned`).
- Issue-number caution: pre-2026-10-14 `#N` references inherited from the
  family history resolve to FAIR-bioHeaders-Specification, not this
  repository ([#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107)).
