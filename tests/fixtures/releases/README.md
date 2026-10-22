# Released schemas for the test-only microdata reader

`fhp-v0.4.0.json` is a byte-for-byte copy of `fhp.json` from
FAIR-bioHeaders-Specification release `v0.4.0`. Release `v0.4.1` changed only
format rules, so it carries the same FHP schema contract and uses this copy too.

`tests/fhp_microdata.py` resolves a record's `schema` value against its
`SUPPORTED_RELEASES` map and validates with the selected released contract.
These copies are test fixtures, not runtime schema bundles; do not edit them.
Add a new release by copying its tagged `fhp.json` and extending
`SUPPORTED_RELEASES`.
