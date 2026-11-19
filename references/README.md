# Declared-reference advisory audit

This consumer implements its part of
[shared issue #241](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/241).
The adapter reads this repository's **current owning declarations** on every run;
it does not score the central inventory's older snapshot or change any pin.

`checker.json` pins the accepted shared checker by source commit and SHA-256.
The runner verifies the checkout HEAD and script bytes before execution. The
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
python3 scripts/reference_audit.py --checker-root /path/to/pinned/shared --checkout FAIR-bioHeaders/FAIR-bioHeaders-Specification=/path/to/pinned/shared --strict
python3 scripts/check_reference_audit_controls.py --checker-root /path/to/pinned/shared
```

The shared checkout must be at the exact checker commit and have all referenced
release tags/history available. Offline controls compare actual authority/local
bytes, then require a digest computed from deliberately different bytes to report
DRIFT and an unmapped query to report QUERY_FAILED. No fixture, pin or source file
is rewritten by these controls. PR checks run adapter/refusal tests and these
actual offline comparisons; they do not gate on live network state.

The scheduled/manual job checks authoritative tag/commit bytes over the GitHub
API with read-only permissions and retains the generated inventory and JSON
report. Its normal exit is advisory: inspect every FRESH/DRIFT/ABSENT/QUERY_FAILED
result and the explicit local/source-set coverage. An unusable declaration or
unverified checker refuses execution with exit 2. Failed queries are not missing
artifacts, and an unperformed comparison is not a pass. No auto-repin runs.

The checks establish fidelity to the declared revision, not adoption, latest-main
currency, biological validity or a new contract release. Other consumers still
need their own actual rollout before the federation-wide issue can close.
