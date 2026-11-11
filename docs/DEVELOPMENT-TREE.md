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
`cc0334b`). The proposal file stays in place unchanged as the 2026-11-10 audit
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
  `docs/SCHEMA-VERSIONS.md`, `conformance/**`) are published by the shared
  repository; anything kept here is a pinned copy, verified by digest, never
  hand-edited.
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
`.github/workflows/shared-parity.yml`. That workflow additionally requires
`copied[]` to equal exactly what `scripts/make_provenance.py` regenerates from
the pinned commit plus its hard-wired companion set — so a copy changes only
as part of a deliberate, generator-reproducible resync, never as a hand edit
or an isolated digest bump. There is no `check_development_tree.py` here
(FHR-Specification's counterpart); whether the two classifications merge into
one script is the open **Q7** below.

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

## Deferred conformance package

The issue-#3 sync was bounded; this package stays at the pre-v0.5.0 family
state, listed in full under `provenance.json` `deferred` and `legacy`:

- `conformance/manifest.json`, the vector tree, `scripts/check_conformance.py`,
  `scripts/make_conformance.py` and `tests/test_conformance.py` (the coherent
  local pre-v0.5.0 generation);
- the 9 `fhp-fasta` vectors the v0.5.0 manifest added or changed (8 new R15/V
  vectors plus the `fhp-fasta-rich` byte update) — validated from the pinned
  upstream tree by the shared-parity workflow, not by local copies;
- `docs/FORMAT.md` (its v0.5.0 copy carries the [R11]–[R15] tokens the v0.5.0
  manifest byte-matches), `docs/JSONLD.md` (no [J9]), `docs/MICRODATA.md`
  (no [M5]) and `docs/FHGFF3.md` as shared copies;
- the v0.5.0-era `jsonld/fhr.*` inputs and the shared git tags the
  schema-selection vectors (V1–V6) resolve against.

## Inherited FHR/FHGFF3 generation (frozen, Q2-gated)

`schemas/core.yaml` (v0.3-era), `fhr.json`, `fhr_linkml.yml`, `fhgff3.json`,
`fhgff3_linkml.yml`, the Pages-era `jsonld/fhr.context.jsonld`,
`jsonld/terms.jsonld`, `jsonld/terms.ttl`, the family docs and the legacy FHR
and FHGFF3 examples are frozen compatibility/history copies. They still build
and validate in this checkout (CI runs the inherited family checks), and FHP
1.1 does not import any of them — it imports `schemas/core-v0.5.yaml`.

## Open questions (maintainer decisions)

Resolved in implementation (recorded here for the audit trail):

- **Q1** — the shared-parity workflow pins
  `fair-bioheaders[jsonld]==0.9.0`, the first verified release that bundles
  the v0.5.0 schemas (0.8.2 bundles FHP only through v0.4.1).
- **Q3** — the 1.1 model imports the vendored `schemas/core-v0.5.yaml` pin
  with the machine-checkable import retarget; the v0.3-era root core stays
  intact pending Q2.
- **Q5** — `CITATION.cff` carries the FHP development identity
  ([#22](https://github.com/FAIR-bioHeaders/FHP-Specification/pull/22),
  commit `c39199a`); FHR records are labeled related history, no FHP DOI is
  claimed.

Still open:

- **Q2 (open — maintainer decision):** after the v0.5.0 sync, does FHP CI
  keep generating and drift-checking `fhr.json`/`fhgff3.json` locally (the
  root `schemas/core.yaml` then becomes the published core copy and the
  v0.3-era generation ends), or shrink to FHP-only checks with FHR/FHGFF3
  retained purely as pinned compatibility fixtures? This also gates the
  deferred family docs and the full conformance-package resync.
- **Q4 (open — maintainer decision):** reuse of the pinned family
  `conformance/manifest.json` versus an FHP-owned vector subset; CI must wire
  to exactly one source.
- **Q6 (open — maintainer decision):** an FHP-specific `Diagram.svg` via
  `scripts/render_diagram.py` — regenerate here, defer, or replace with a
  pointer to the shared diagram? `Diagram.svg` is currently the inherited FHR
  schema diagram kept as provenance.
- **Q7 (open — maintainer decision):** the documentation/enforcement shape
  itself. This document adopts the `docs/DEVELOPMENT-TREE.md` name (the
  FHR-Specification convention), but enforcement stays with
  `provenance.json` + `scripts/check_shared_parity.py` rather than a
  `check_development_tree.py`-style classifier. Merging the two into one
  script and one doc is a maintainer call; until then this page names the
  single enforcement point above.

## Working references

- The proposal's §2 inventory, §3 pin table and §8 audit commands remain the
  detailed 2026-11-10 record
  ([DEVELOPMENT-TREE-PROPOSAL.md](DEVELOPMENT-TREE-PROPOSAL.md)).
- Per-file classification for every path in this tree: `provenance.json`
  (`copied` / `imports` / `legacy` / `owned` / `deferred`).
- Issue-number caution: pre-2026-10-14 `#N` references inherited from the
  family history resolve to FAIR-bioHeaders-Specification, not this
  repository ([#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107)).
