# The FHP development tree — proposal (issue #2)

**Status: proposal.** This document is the canonical-tree and
schema-ownership proposal for
[FHP-Specification#2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2)
(federation tracker
[FAIR-bioHeaders-Specification#158](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/158),
migration record
[#107](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/107)).
It changes no schema bytes. On adoption it becomes `docs/DEVELOPMENT-TREE.md`
(the FHR-Specification convention, enforced there by
`scripts/check_development_tree.py`) with a companion check script wired for
issue #3.

Audited 2026-11-10 against:

| Reference | Value |
| --- | --- |
| This branch | `codex/fhp-2-tree`, base `664a11c` (FHP-Specification `origin/main` at audit) |
| Shared spec `origin/main` | `9db66060b0d835be56cd94c783ac28459935c32b` ("Draft INSDC submission-readiness profile for FHR (#209)") |
| Shared spec tag `v0.5.0` | annotated tag object `7150f74cf447de5694b8938c705d5a5896eaeacd`, peels to commit `170e677fbb6726a3f765373dbe1f214820000be7` ("Release v0.5.0 (extension fields: FHR 2.1, FHP and FHGFF3 1.1)", 2026-11-04) |
| Shared spec tag `v0.4.0` release commit | `84c2f90ab0e97c81d8afbf33eafe80ebade7a009` (as already recorded in `tests/fixtures/fhp/v0.4.0/PROVENANCE.json`) |
| Schema versions (`schemas/versions.json` @ shared main) | v0.4.0–v0.4.2: FHP `"1.0"`; v0.5.0: FHP `"1.1"` (x- extension fields) |
| w3id check | `https://w3id.org/fair-bioheaders/fhp/v0.5.0` → 200 → `.../FAIR-bioHeaders-Specification/v0.5.0/fhp.json`; `.../fhp/v0.4.0` likewise |
| Toolkit (`fair-bioheaders` on PyPI) | `0.8.2` exists (first release with the FHP serializations, per #1); latest is `0.9.0` as of 2026-11-10. This repository's CI still pins legacy `fhr==0.3.3` |

## 1. Decision summary

**Chosen model: the FHR-style single-tree classification, plus an FHGFF3-style
machine-readable pin file, plus formalization of the pinned-fixture pattern
this repository already invented.**

Three patterns exist in the federation:

1. **FHR-Specification** keeps the whole family tree at the repository root,
   classifies every file in `docs/DEVELOPMENT-TREE.md`, pins byte-identical
   published copies with recorded SHA-256 digests enforced by
   `scripts/check_development_tree.py`, and adds a live `published-files`
   workflow that diffs them against shared `main`.
2. **FHGFF3** put the FAIR header development into a separate `header/` tree
   that is a byte-for-byte copy of the shared model at a pinned commit
   (`header/provenance.json`, verified by `scripts/check_header_parity.py` and
   `.github/workflows/header-parity.yml`). That pattern was chosen there
   because the rest of the FHGFF3 repository is an unrelated inherited
   biodatamodels/gff-schema feature model.
3. **FHP-Specification (this repository, de facto)** keeps the family tree at
   root *and* has already begun vendoring: `schemas/core-v0.4.yaml` is a
   header-annotated byte-copy of the shared core pinned to the v0.4.0 release
   commit, `fhp_linkml.yml` imports it, and `tests/fixtures/fhp/v0.4.0/` plus
   `tests/fixtures/releases/` pin released-contract copies with a
   `PROVENANCE.json` (source repo, release, commit, per-file SHA-256).

FHP must not copy FHGFF3's separate-tree layout wholesale: this repository is
the **canonical publication surface for the FHP JSON-LD serialization**, not
merely a development copy. `FAIR-bioHeaders-Tools/bioheaders/jsonld.py` states
"the FHP context's canonical raw-main URL is FHP-Specification" and resolves
`https://raw.githubusercontent.com/FAIR-bioHeaders/FHP-Specification/main/jsonld/fhp.context.jsonld`;
`docs/FHP-MICRODATA.md`, `jsonld/fhp.*` and the microdata/JSON-LD fixtures
exist only here (they are absent from the shared repository), and
`.github/workflows/jsonld-pages.yml` publishes this tree's `jsonld/` under the
`w3id.org/fair-bioheaders/fhp/vX.Y.Z/jsonld/` aliases (FHP#10 preflight).
Moving those paths would break the toolkit and the alias chain. The
classification therefore applies **in place** (FHR pattern), while the
pinned-upstream bookkeeping generalizes the existing `PROVENANCE.json` idea
into one root file (FHGFF3 `header/provenance.json` pattern) so that issue #3
has a single machine-readable pin to consume.

**Canonical ownership, one line each:**

- The **published FHP metadata contract** is `fhp.json` in
  FAIR-bioHeaders-Specification at each release tag (w3id URLs). It is never
  edited here; this repository's root `fhp.json` is a pinned compatibility
  copy used by local validation, generated `fhp.json` included.
- The **FHP LinkML model** develops in this repository on branches
  (`fhp_linkml.yml`), publishes through the shared repository, and the shared
  published copy is then synced back here. Today `main` here holds the FHP 1.0
  model revision; the shared v0.5.0 line carries FHP 1.1.
- The **FHP JSON-LD context/vocabulary, microdata binding and their fixtures**
  (`jsonld/fhp.*`, `docs/FHP-MICRODATA.md`, the FHP serialization examples and
  readers in `tests/`) are owned and published **here** — this is their
  canonical source. They are FHP development outputs coordinated into shared
  records (shared `CHANGELOG.md` names this repository's copy as the toolkit
  bundle source, its #12), not byte-copies of shared files.
- **Shared core/imports** (`schemas/core.yaml`, `schemas/shared.yaml`,
  `schemas/versions.json`, `docs/FORMAT.md`, `docs/SCHEMA-VERSIONS.md`,
  `conformance/manifest.json` and the family vectors) are published by the
  shared repository; anything kept here is a pinned copy, verified by digest,
  never hand-edited.
- The **active converter/validator** is FAIR-bioHeaders-Tools
  (`pip install fair-bioheaders`). This repository creates and advertises no
  FHP-specific converter; the archived FHT-File-Converter is not a dependency.

## 2. Tree inventory (verified by digest, 2026-11-10)

Comparison method: `git -C ../FAIR-bioHeaders-Specification show
origin/main:<path>` / `show 170e677:<path>` extracted to temp files and
`cmp`/SHA-256 against the working tree (commands in §8). Shared `v0.5.0` and
shared `origin/main` are byte-identical for every FHP artifact examined below
**except** `examples/fhp/rich-predicted.fhp.yaml` (changed post-tag by
`e1e5998` "Match the FHP rich-predicted example with its companion copies
(#201)": an added `nameType: Personal` comment/field demonstration).

### 2a. FHP-owned (canonical here)

- `fhp_linkml.yml` — FHP development model (imports `schemas/core-v0.4`; the
  vendored core pin, see §2d).
- `docs/FHP-MICRODATA.md`, `jsonld/fhp.context.jsonld`,
  `jsonld/fhp.terms.jsonld`, `jsonld/fhp.terms.ttl` — published from here;
  toolkit- and w3id-dependent paths. Do not move or rename.
- `scripts/make_jsonld.py` (FHP context/vocabulary generation,
  `FHP_RELEASE_ALIAS = https://w3id.org/fair-bioheaders/fhp/vX.Y.Z/jsonld/`),
  `scripts/build_pages.py`, `.github/workflows/jsonld-pages.yml`.
- `tests/fhp_microdata.py`, `tests/test_fhp_jsonld.py`,
  `tests/test_fhp_microdata.py`, `tests/test_fhp_schema.py`,
  `tests/fixtures/fhp_stub.yaml`, `tests/fixtures/fhp/v0.4.0/` (with
  `PROVENANCE.json`), `tests/fixtures/releases/fhp-v0.4.0.json` (+README).
- FHP serialization examples that do not exist in the shared repository:
  `examples/fhp/*.microdata.fhp.html`, `examples/fhp/*.fhp.jsonld`,
  `examples/fhp/rich-microdata.fhp.json` (14 files beyond the 7 shared
  examples).
- `.github/schema-baseline-fhp.json` (local FHP drift baseline; the FHR/FHGFF3
  baselines are inherited, §2e).

### 2b. Byte-identical to shared `origin/main` today (compatibility copies)

- `schemas/shared.yaml` (0e7e08d52c73…@main — unchanged v0.4→v0.5).
- `fhr_mappings.yml`; `LICENSE`; `assessment/manifest.json`.
- 22 unchanged `fhp-fasta` conformance vectors: `valid/{bgzf,
  comments-and-blank-lines,crlf,database-source,gzip,lf,mixed-sources,
  no-final-newline}` (8) and all 14 `conformance/invalid/fhp-fasta-*` files
  that also exist locally (§2c lists the 4 new invalid and 4 new valid
  additions).

### 2c. Pinned copies that have diverged from the v0.5.0 line (sync in #3)

These are exactly the files downstream CI in issue #3 must resynchronize to
the pin in §3; each is currently at the older (v0.4.0/v0.3-era) family state
because this tree predates the v0.5.0 sync:

- `fhp.json` — local = released **FHP 1.0** bytes (sha256 `e3f8f452…`,
  matching the v0.4.0 pin in `tests/fixtures/fhp/v0.4.0/PROVENANCE.json`);
  v0.5.0 = FHP 1.1 with `x-` extension fields (`2409739d…`).
- `fhp_linkml.yml` — local generates the 1.0 contract; shared 1.1 model is
  `980eaa51…`.
- `schemas/core.yaml` — local is the **v0.3-era** core (float `schemaVersion`,
  loose patterns) still used by the inherited local `fhr.json`/`fhgff3.json`
  generation; shared is `2bd657ec…`.
- `docs/FHP.md` — local still says "draft, not released"; shared published doc
  is `a328ad7f…` (FHP 1.0 released, v0.5 doc for 1.1).
- `docs/FORMAT.md` — local is the "FHR v0.3" copy; shared `482f3553…`.
- `conformance/manifest.json` — local predates the v0.5 FHP vectors;
  shared `8ab8f7f4…`.
- `examples/fhp/{example.fhp.fasta,minimal-database.fhp.json,minimal-mixed.fhp.json,minimal-predicted.fhp.json,rich-database.fhp.json,rich-mixed.fhp.yaml,rich-predicted.fhp.yaml}`
  and `conformance/valid/fhp-fasta-rich.fhp.fasta`,
  `conformance/invalid/fhgff3-annotates-fhp.fhgff3.gff3` — differ from the
  v0.5.0 bytes.
- **Missing here but in the v0.5.0 pin set:** `schemas/versions.json`,
  `docs/SCHEMA-VERSIONS.md`, and 8 new vectors:
  `valid/{fhp-fasta-escaped-record-markers,fhp-fasta-extension-fields,fhp-fasta-schema-canonical-raw-main,fhp-fasta-schema-raw-tag}.fhp.fasta`,
  `invalid/{fhp-fasta-extension-nested,fhp-fasta-extension-older-release,fhp-fasta-extension-older-version,fhp-fasta-schema-release-without-type}.fhp.fasta`,
  plus a `SUPPORTED_RELEASES` extension in `tests/fhp_microdata.py` for a
  future `fhp-v0.5.0.json` fixture copy.
- Inherited published copies also stale (sync only if §4 Q2 keeps FHR/FHGFF3
  generation here): `fhr.json`, `fhr_linkml.yml`, `fhgff3.json`,
  `fhgff3_linkml.yml`, `.github/schema-baseline{,-fhgff3}.json`,
  `jsonld/{fhr.context.jsonld,terms.jsonld,terms.ttl}` (all three differ from
  shared `origin/main`; they are the pre-v0.4.2-companion-era Pages copies),
  and the family docs (`docs/{TERMS,JSONLD,MICRODATA,MAPPINGS,SCHEMAORG-EXPORT,TOOL_COMPATIBILITY,FAIR_HEADER_GUIDELINE,FHGFF3}.md`).

### 2d. Vendored pin already present

- `schemas/core-v0.4.yaml` = 8-line provenance header + byte-for-byte shared
  `schemas/core.yaml` at the **v0.4.0 release commit
  `84c2f90ab0e97c81d8afbf33eafe80ebade7a009`** (verified by diff: only the
  header lines are added). `fhp_linkml.yml` line 19 imports
  `schemas/core-v0.4`. Keep the mechanism; generalize the bookkeeping into
  the root pin file (§3) and replace the snapshot itself when #3 syncs the
  model to the 1.1 line (then import `schemas/core.yaml` like shared, or a
  `core-v0.5.yaml` pin if the v0.3 `core.yaml` stays for FHR compatibility —
  maintainer choice, §4 Q2).

### 2e. Inherited family machinery (retained dependencies, per the FHR precedent)

`scripts/{validate_examples,check_linkml,check_conformance,check_schema_drift,make_conformance,check_release,project_mixs,render_diagram}.py`,
`json-schema-generator.py`, the `tests/` suite, `.github/workflows/` and
`specs/**`, `assessment/**`, `mappings/**` run the **whole family** (FHR, FHP,
FHGFF3) from this checkout: e.g. `validate-specification.yml` validates
`fhgff3.json`/`examples/fhgff3`, `check-schema-drift.yml` regenerates all
three schemas, `make_conformance.py` pins `FHP_SCHEMA =
https://w3id.org/fair-bioheaders/fhp/v0.4.0`. Per the #2 checklist, inherited
artifacts are **not deleted merely because they are inherited**; #3 decides
what stays live versus becomes a pinned compatibility fixture (§4 Q2).
`scripts/tool_survey/**` and `specs/001–013` are the same provenance/
citation-by-URL retention cases FHR classified in its §3b/§4.

## 3. Canonical source + pin table (what #3 CI consumes)

Recommended: one root machine-readable pin file `provenance.json` (schema
mirroring FHGFF3's `header/provenance.json`: `source.repository/url/commit/
ref` + `copied[] {local, upstream, sha256}` + `imports[]`), verified by
`scripts/check_shared_parity.py` (local digests; `--upstream PATH` against a
checkout of the pinned commit) and a `shared-parity.yml` workflow modeled on
FHGFF3's `header-parity.yml` (checkout the pinned shared commit; run parity;
then run the pinned shared tree's `scripts/check_conformance.py` with a named
`fair-bioheaders` release, currently `0.8.2` or `0.9.0` — §4 Q1).

Pin baseline recommended: the **immutable v0.5.0 release commit**
`170e677fbb6726a3f765373dbe1f214820000be7` (annotated tag object
`7150f74cf447de5694b8938c705d5a5896eaeacd`), with a companion live
"drift-against-shared-main" note rather than a byte-pin on `9db66060b0d835be56cd94c783ac28459935c32b`
(`origin/main` at audit), because raw-main is a current-contract link, not an
immutable version. Every digest below is `git show 170e677:<path> | shasum -a 256`
computed 2026-11-10 (all also equal `origin/main` except where marked †):

| Upstream path (FAIR-bioHeaders-Specification) | SHA-256 at the v0.5.0 commit | Local target |
| --- | --- | --- |
| `fhp.json` | `2409739d4a223164ca368f93afa78c8f1e3809fb04ec46cc9a793cc5aaaba427` | `fhp.json` (compat copy), `tests/fixtures/releases/fhp-v0.5.0.json` (new) |
| `fhp_linkml.yml` | `980eaa51f07fe27630545c94eb613df1aab30de431fd66a12456936ed7cc7797` | `fhp_linkml.yml` |
| `schemas/core.yaml` | `2bd657ece8c8cbfb4dfbba1f68cb3f708c1ab91baa0fcd50d97ddc58b7e96b5e` | `schemas/core.yaml` / `core-v0.5.yaml` (Q2) |
| `schemas/shared.yaml` | `0e7e08d52c739cf245ed76093f22b6f37d6d6e4c4db76b1007619d60ef6a1043` | `schemas/shared.yaml` (already identical) |
| `schemas/versions.json` | `a570c2a5b742e02ecfec5ebc548775092e4ebc51bd272fef164d26b11efc9e61` | `schemas/versions.json` (new) |
| `docs/FHP.md` | `a328ad7f544e4fe2757e1a47787b16280ad069f6f94f12f46c1986de46481e9b` | `docs/FHP.md` |
| `docs/FORMAT.md` | `482f3553963ca707c1ac2313df167abfc3f6cd100c09582c313ec9b3c5eea5e8` | `docs/FORMAT.md` |
| `docs/SCHEMA-VERSIONS.md` | `08213b53f909977a0247836c72e4851da58da5044f03558f122cd5f8d5f7e433` | `docs/SCHEMA-VERSIONS.md` (new) |
| `conformance/manifest.json` | `8ab8f7f4ee592573650973d30dc3e422c22b62b08c6b0b9f7839e12c5e4169ea` | `conformance/manifest.json` |
| `conformance/valid/fhp-fasta-*.fhp.fasta` (13 files) and `conformance/invalid/fhp-fasta-*.fhp.fasta` (18 files) | per-file digests computable from the pinned commit; 22 already match locally (§2b) | same paths; 8 vectors are additions, 1 (`valid/fhp-fasta-rich`) is a content update |
| `examples/fhp/{example.fhp.fasta,minimal-database.fhp.json,minimal-mixed.fhp.json,minimal-predicted.fhp.json,rich-database.fhp.json,rich-mixed.fhp.yaml}` | digests in §8 | same paths; `rich-predicted.fhp.yaml` † differs at `origin/main` (`b7efdbc30128…` vs `27a4d291db0a…` at the tag) |
| vocabulary companion at the v0.4.0 release (JSON-LD test reader fixture, keep alongside a future 0.5 pin) | `tests/fixtures/fhp/v0.4.0/PROVENANCE.json` already pins `fhp.json` `e3f8f452…` + `terms.ttl` `0c641879…` @ `84c2f90a…` | unchanged — released fixtures are immutable |

Local-owned canonical files (§2a) get **no upstream pin** — the parity check
must explicitly exclude them (record them under a `owned:` key in
`provenance.json` so an unclassified new path fails the check, as FHR's
strictness rule does for `jsonld/` and `examples/`).

## 4. Identity trimming and open questions

### Done on this branch (non-controversial, text only)

- `README.md`: replaced the copied shared-publication README body with
  FHP/protein-FASTA scope; corrected "FHP is a draft" to the accurate
  released-contract (shared v0.4.0 FHP 1.0; shared v0.5.0 FHP 1.1 with `x-`
  fields) versus development-repository status; re-pointed CI badges to this
  repository's own workflows; removed the inherited FHR specification/converter
  DOI banners (FHR citations retained, clearly labeled as FHR history — no
  invented FHP DOI); routed conversion/validation to FAIR-bioHeaders-Tools
  with no FHP-specific converter; linked this proposal, #2/#3/#6 and #107/#158;
  added the historical-issue-number caution (this repository reuses the family
  history; pre-2026-10-14 `#N` references resolve to
  FAIR-bioHeaders-Specification, #107/#108).
- `CONTRIBUTING.md`: released-specification issues routed to the shared
  repository; fixed the `FHR-File-Converter` link text (retired name; URL was
  already FAIR-bioHeaders-Tools); FHP-scoped the metadata-coordination
  paragraph.

### Deliberately not touched

- `AGENTS.md` — shared sections must stay byte-identical across the five
  repositories; it already cites the v0.5.0 URLs (664a11c).
- All contract/schema/fixture bytes — synchronization belongs to #3 with the
  parity wiring, not to an identity-trim commit.
- `CITATION.cff` — currently `title: FHR Specification`; see #6 below.
- `Diagram.svg` — the FHR schema diagram (rendered by
  `scripts/render_diagram.py`); retained as inherited provenance.
- `.claude/`, `.specify/`, `specs/**`, `assessment/**`, `mappings/**`,
  `scripts/tool_survey/**`, `fhr.*`/`fhgff3.*` files — retained pending §4 Q2
  and the "do not remove artifacts merely because they are inherited" rule.

### Open questions (maintainer decisions)

- **Q1 (for #3):** which named toolkit release does conformance pin —
  `fair-bioheaders==0.8.2` (first with FHP serializations, per #1) or `0.9.0`
  (current on PyPI at audit)? FHGFF3's parity workflow pins `0.8.1`
  (`[jsonld]` extra); align deliberately.
- **Q2 (for #3/#2):** after the v0.5.0 sync, does FHP CI keep generating and
  drift-checking `fhr.json`/`fhgff3.json` locally (root `schemas/core.yaml`
  must then also become the published core copy, ending the v0.3-era
  `core.yaml`), or shrink to FHP-only checks with FHR/FHGFF3 retained purely
  as pinned compatibility fixtures? This decides whether
  `docs/FHGFF3.md`-family docs stay live.
- **Q3 (for #3):** `fhp_linkml.yml` import target after sync: shared-style
  `schemas/core.yaml` (if Q2 retires the local v0.3 core) or a renamed
  `schemas/core-v0.5.yaml` pin (if the v0.3 core must stay for legacy FHR
  generation)? Avoid a second divergent shared core (#3 checklist).
- **Q4 (for #3):** reuse of the pinned family `conformance/manifest.json`
  versus an FHP-owned vector subset; wire CI to exactly one source
  (#3 checklist names this fork explicitly).
- **Q5 (for #6):** `CITATION.cff` identity. Needed: title/repository-code/url
  pointing at this development repository without renaming the registered
  FHR bibliographic title or implying Zenodo `10.5281/zenodo.6762549`
  identifies FHP development; keep the 2024 paper and FHR records as clearly
  labeled related citations; cite the published FHP contract as the shared
  repository release (v0.5.0, FHP 1.1) and verify any version DOI against
  primary records — do not invent one. Coordinate FHR-Citation and the
  website (fair-bioheaders.github.io, FHR-Citation/AUDIT.md pattern) — those
  are the downstream consumers of the README/CFF identity changes.
- **Q6:** an FHP-specific `Diagram.svg` via `scripts/render_diagram.py` —
  regenerate here, defer, or replace with a pointer to the shared diagram?
- **Q7 (for #2 adoption):** rename this file to `docs/DEVELOPMENT-TREE.md` on
  adoption and add `scripts/check_development_tree.py`-style digest
  classification, or implement §3's `provenance.json` +
  `check_shared_parity.py` alone? The two can be one script; the doc should
  name exactly one enforcement point.

### Downstream consumers affected by identity/trims (issue #6 coordination)

- **FAIR-bioHeaders-Tools** (`bioheaders/jsonld.py`,
  `bioheaders/fhp_microdata.py`): raw-main `jsonld/fhp.context.jsonld` on
  *this* repository is canonical — paths there are load-bearing; the FHP
  context/vocabulary bytes themselves are FHP-owned and unchanged by this
  branch.
- **Website (fair-bioheaders.github.io):** repository-role/citation/link
  cleanup pattern per spec#158 (website#22/PR#24); consumes README identity
  and citation records.
- **FHR-Citation:** `citation.bib` + AUDIT.md records; CFF/title changes must
  match it rather than rename registered FHR records.
- **Shared examples/publication:** only receive coordinated PRs (#107);
  nothing in §4 renames shared paths.
- **w3id + GitHub Pages:** `fhp/vX.Y.Z/jsonld` aliases depend on this
  repository's `jsonld/` layout and release tags; untouched here.

## 5. Concrete step list (parallel PRs after this is merged)

PR-A (issue #3, CI/pin):
1. Add `provenance.json` (§3 digests, `source.commit = 170e677…`,
   `owned:` exclusions for §2a) and `scripts/check_shared_parity.py`
   (port of FHGFF3's `check_header_parity.py` semantics).
2. Sync §2c bytes to the v0.5.0 pin: `fhp.json`, `fhp_linkml.yml`,
   `schemas/{core,shared,versions}`, `docs/{FHP,FORMAT,SCHEMA-VERSIONS}.md`,
   `conformance/**` (9 new vectors, 2 updates, manifest), the 6 stable
   `examples/fhp` files + Q3/Q4 answers; add
   `tests/fixtures/releases/fhp-v0.5.0.json` and extend
   `tests/fhp_microdata.py` `SUPPORTED_RELEASES` (historical fixtures stay
   immutable); regenerate `.github/schema-baseline-fhp.json` via
   `python scripts/check_schema_drift.py --schema fhp.json --baseline
   .github/schema-baseline-fhp.json --update` in the same PR with an explicit
   reviewed diff (this is the contract-move, not an incidental cleanup —
   schema semantics themselves do not change; bytes come from shared).
3. Replace `pip install fhr==0.3.3` with the Q1 toolkit release; stop skipping
   `--require-format fhp-fasta`; wire `shared-parity.yml` (pinned-commit
   checkout + parity + conformance) and update `make_conformance.py`'s
   `FHP_SCHEMA` selection tests for v0.5.0 schema URLs
   (`fhp-fasta-schema-raw-tag`/`-canonical-raw-main` coverage).
4. Update `tests/test_fhp_schema.py` (it currently rejects `"1.1"`) to the
   synced contract, keeping FHP-1.0 acceptance tests against the pinned
   released fixture, not against rewritten history.

PR-B (issue #6, citation): Q5 checklist; touches `CITATION.cff`, the README
citation section only, and links from FHR-Citation/website PRs. No schema,
fixture or workflow bytes.

PR-C (this issue's residue, #2): adopt/rename this doc per Q7, resolve Q6,
and re-run the #2 acceptance boxes; close #2 only after #158's "FHP
identity/trimming/source classification" box can be checked.

#1 (tracker) then reads: tree/source = #2 (this doc + PR-C), CI pin = PR-A,
citation = PR-B — independent of each other after merge.

## 6. What this proposal does not do

No file deletions; no schemaVersion, contract or fixture edits; no
new pin to an untagged moving ref; no adoption/release claim; no invented
DOI, identifier or provenance. Shared publication authority stays with
FAIR-bioHeaders-Specification; repository setup does not authorize changing
published contracts.

## 7. Historical issue-number note

Before the October 14, 2026 rename, `FHR-Specification` was this family's
shared repository; `#N` links in inherited text mean
FAIR-bioHeaders-Specification issues (see #107/#108), while `#N` links added
after that date resolve to the type repositories.

## 8. Audit record (commands)

```sh
# shared-spec truth (checkout was on a stale branch; only origin/main/used):
git -C ../FAIR-bioHeaders-Specification rev-parse origin/main        # 9db6606…
git -C ../FAIR-bioHeaders-Specification rev-parse 'v0.5.0^{commit}'  # 170e677…
git -C ../FAIR-bioHeaders-Specification show v0.5.0:schemas/versions.json
# per-file comparison (cmp + shasum) of this worktree against
#   git -C ../FAIR-bioHeaders-Specification show origin/main:<path>
#   git -C ../FAIR-bioHeaders-Specification show 170e677:<path>
# for fhp.json, fhp_linkml.yml, fhr/fhgff3 counterparts, schemas/*, docs/*,
# examples/fhp/*, conformance/{valid,invalid}/*fhp*, conformance/manifest.json
# (script: session temp pincompare.py; full digests reproduced in §3)
cmp <(git -C ../FAIR-bioHeaders-Specification show 170e677:schemas/core.yaml) \
    <(tail -n +9 schemas/core-v0.4.yaml)   # core-v0.4.yaml == v0.4.0 core + header
# sibling patterns (read-only):
git -C ../FHGFF3 show origin/main:header/provenance.json
git -C ../FHGFF3 show origin/main:.github/workflows/header-parity.yml
git -C ../FHR-Specification show origin/main:docs/DEVELOPMENT-TREE.md
# consumers:
gh issue view 158 --repo FAIR-bioHeaders/FAIR-bioHeaders-Specification
gh issue view 1 3 6 --repo FAIR-bioHeaders/FHP-Specification
rg -n 'FHP-Specification' ../FAIR-bioHeaders-Tools/bioheaders
curl -s https://pypi.org/pypi/fair-bioheaders/json | jq .info.version  # 0.9.0
curl -sIL https://w3id.org/fair-bioheaders/fhp/v0.5.0                   # 200 → tag raw fhp.json
```
