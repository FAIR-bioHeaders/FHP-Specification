# Released schemas for the test-only microdata reader

`fhp-v0.4.0.json` is a byte-for-byte copy of `fhp.json` from
FAIR-bioHeaders-Specification release `v0.4.0`. Release `v0.4.1` changed only
format rules, so it carries the same FHP schema contract and uses this copy too.

`fhp-v0.5.0.json` is a byte-for-byte copy of `fhp.json` from release `v0.5.0`
(FHP `1.1`), and `fhp-v0.6.0.json` of `fhp.json` from release `v0.6.0` (FHP
`1.2`, dotted BUSCO dataset versions, FAIR-bioHeaders-Specification#170). The
two v0.6.0-era copies (`fhp.json` at the tree root and this fixture) are
digest-pinned to shared commit `0ae18b00ee4bd71ab2dc28bae706b0f9d195076b` in
`provenance.json` per FHP-Specification#31.

`tests/fhp_microdata.py` resolves a record's `schema` value against its
`SUPPORTED_RELEASES` map and validates with the selected released contract.
These copies are test fixtures, not runtime schema bundles; do not edit them.
Add a new release by copying its tagged `fhp.json` and extending
`SUPPORTED_RELEASES`.
