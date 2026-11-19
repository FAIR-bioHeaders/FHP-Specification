# Declared-reference advisory audit

This consumer implements its part of
[shared issue #241](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/241).
The adapter reads this repository's **current owning declarations** on every run;
it does not score the central inventory's older snapshot or change any pin.

`checker.json` pins the accepted shared checker by source commit and SHA-256.
The runner verifies the approved repository, full commit, canonical nonsymlink path, checkout HEAD, immutable `git show <commit>:<path>` bytes and script digest before execution. The working file must equal that committed blob even if both it and the recorded digest were tampered with. The verified engine runs under Python `-I`, isolating unverified adjacent modules. The
engine is not copied here. Schema, model, suite, carrier and historical copy
pins remain unchanged. A checker-code refresh is a separate reviewed change.

## Scope

Current declarations include 54 copied entries, 24 explicitly historical pinned
entries and 6 imports in `provenance.json`, immutable v0.4.0 fixture provenance,
and the tag/authority statements in `.github/schema-baseline-refs.json`. The 24
historical files omitted by the initial central snapshot are explicitly covered
at their recorded commit; they are not reclassified as new releases.
`classification.json` identifies the already-recorded v0.5.0 overrides and audits
the existing legacy `schemas/core-v0.4.yaml` header/payload against its stated
v0.4.0 release. This adds provenance coverage without moving imports or bytes.

Complete source patterns cover the release-owned FHP vector set. The local tree
also contains deliberately owned/historical files; existing shared-parity checks
retain their local classification and exact adjustment checks. Canonicalized
review-baseline JSON is not falsely compared as a byte-copy of a released file:
its actual authority claims are checked, and existing semantic guards remain.
Dated `liveMain`/sweep observations, local source, adapted parser implementations,
package/action/tool dependencies and biological source evidence are distinguished
from the five contract-reference classes.

The existing main-push JSON-LD Pages workflow deploys only when its preflight says
Pages is configured. Recheck that live condition before any merge; this audit
port does not itself grant publication authority.

## Local commands and evidence

```sh
python3 -m unittest discover -s tests -p test_reference_audit.py -v
python3 scripts/reference_audit.py --inventory-only
python3 scripts/reference_audit.py --checker-root /path/to/pinned/shared --checkout FAIR-bioHeaders/FAIR-bioHeaders-Specification=/path/to/pinned/shared
python3 scripts/check_reference_audit_controls.py --checker-root /path/to/pinned/shared
```

The shared checkout must be at the exact checker commit and have all referenced
release tags/history available. Required controls use a temporary synthetic Git
repository, exercising FRESH, deliberately changed-byte DRIFT, confirmed ABSENT,
and unmapped QUERY_FAILED outcomes with the actual checker. They never depend on
current owning references remaining fresh. PR checks retain the current-reference
report without gating on its findings; existing native contract/parity gates
remain independent. An always-run fallback retains QUERY_FAILED if setup or
execution produced no usable report. Execution failures may still fail the job;
reference findings do not. No fixture, pin or source file is rewritten.

The scheduled/manual job checks authoritative tag/commit bytes over the GitHub
API with read-only permissions and retains the generated inventory and JSON
report. Its normal exit is advisory: inspect every FRESH/DRIFT/ABSENT/QUERY_FAILED
result and the explicit local/source-set coverage. An unusable declaration or
unverified checker refuses execution with exit 2. Failed queries are not missing
artifacts, and an unperformed comparison is not a pass. No auto-repin runs.

The checks establish fidelity to the declared revision, not adoption, latest-main
currency, biological validity or a new contract release. Other consumers still
need their own actual rollout before the federation-wide issue can close.

Controlling source repository/URL declarations are validated before normalization; missing or unexpected authorities refuse the run instead of being silently replaced with the publication authority. Historical observations and namespace `$id` values are not retrieval inputs.

The adapter also reads the actual `SUPPORTED_RELEASES` aliases and copy locator in `tests/fhp_microdata.py`, plus the release/commit/digest/source URLs of the vocabulary pin in `scripts/make_jsonld.py`. Each alias is compared at its own tag against the reader's actual local copy; canonicalized review baselines are not substituted for those copies. Source ref/tag mismatches and unsupported per-entry source overrides refuse normalization.
