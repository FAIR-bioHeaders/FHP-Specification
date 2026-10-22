# FHP HTML microdata (draft binding)

**Status: draft binding proposal; the FHP 1.0 contract it binds is released.** This document defines the type-specific FHP
binding for HTML microdata. It is developed in FHP-Specification (#5, feature 006
follow-up F-02) and must be published through FAIR-bioHeaders-Specification before it is
adopted. No FHP release, tag or DOI is created here. The toolkit reader and writer are not shipped
in this repository; they are implemented in
[FAIR-bioHeaders-Tools#98](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools/pull/98)
(for [FAIR-bioHeaders-Tools#58](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools/issues/58))
and ship in the first toolkit release that includes that change.
The website consumer
([fair-bioheaders.github.io#21](https://github.com/FAIR-bioHeaders/fair-bioheaders.github.io/issues/21))
and the family builder
([fair-bioheaders.github.io#15](https://github.com/FAIR-bioHeaders/fair-bioheaders.github.io/issues/15))
are coordinated with this binding and are not updated by it. The FHP HTML added by
website PR #27 deliberately carries no microdata until this contract exists.

This binding **reuses** the family rules in [MICRODATA.md](MICRODATA.md) and
[FORMAT.md](FORMAT.md) R7 and R9. It does not restate or change them; it records only how
FHP differs from FHR. Where this page and the shared rules could be read differently, the
shared rules win.

## Record scope and itemtype

- [F1] A document holds exactly one FHP item scope: an element with `itemscope` whose
  `itemtype` tokens include the **raw-main FHP schema URL**
  `https://raw.githubusercontent.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/main/fhp.json`.
  The pre-rename URL
  `https://raw.githubusercontent.com/FAIR-bioHeaders/FHR-Specification/main/fhp.json`
  is the same file and the same item type. This is the same rule as M1 with the FHP URL:
  a document with no FHP scope, or with more than one, is invalid.
- An element with the FHR `itemtype` is **not** an FHP record, even when its properties
  look protein-specific. FHP is never identified by the FHR itemtype, and an FHP file is
  never validated against `fhr.json` ([FHP.md](FHP.md) P2).
- The `itemtype` is the raw-main URL, exactly as
  [SCHEMA-VERSIONS.md](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/blob/main/docs/SCHEMA-VERSIONS.md)
  fixes it for microdata. The record's own `schema` property carries the URL that selects
  the contract version (raw-main, a release tag or its w3id form; see F2).
- FHP requiredness is the FHP contract, not FHR's: `proteome` and `sourceType` are
  required; `genome`, `masking`, `vitalStats`, `assemblySoftware` and the other
  genome-only FHR fields are not FHP properties at all, so an FHP scope that carries them
  fails validation.

## Schema selection and unsupported versions

- [F2] The `schema` property selects the contract version, by the fixed-version rules
  V1 to V4 of
  [SCHEMA-VERSIONS.md](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/blob/main/docs/SCHEMA-VERSIONS.md):
  a raw-main URL selects the reader's current FHP schema, a raw release-tag URL
  (`.../vX.Y.Z/fhp.json`) or its w3id form (`https://w3id.org/fair-bioheaders/fhp/vX.Y.Z`)
  selects that release's schema. Matching is exact.
- The reader resolves the selection **before** converting untyped values or
  validating: `main` uses the current schema, a supported release uses that release's
  schema, and an unavailable release is rejected. The test-only reader carries the
  released FHP `"1.0"` contract from v0.4.0, also used by v0.4.1 (which changed only format
  rules); `v999.0.0` and any other release it does not carry are unsupported-version.
- A `schema` value that is not an FHP schema URL, a release the reader does not have, or
  a `schemaVersion` the selected schema does not accept is **unsupported-version**. The
  document is rejected; it is not checked against another schema. FHP 1.0 is released
  in shared v0.4.0 as the string `"1.0"`, and this development tree now carries that
  released contract; a numeric `1` is not a released FHP contract. A reader uses the
  selected schema's own `schemaVersion` rule, and a writer copies the value the record
  already has.
- The `schema` and `schemaVersion` properties are ordinary properties; they are the same
  values the YAML and JSON forms carry.

## Property bindings

Every FHP field is bound the same way as in [MICRODATA.md](MICRODATA.md): `itemprop`
names the field, nested objects introduce an item scope, arrays use a typed container
whose children are `itemprop="item"`, and typed scalars carry `data-fhr-type`. The table
gives the FHP shape; the shared rules (M1 to M4, R7, R9) apply unchanged.

| Field | JSON type | Microdata shape | Notes |
| --- | --- | --- | --- |
| `schema` | string | string | An FHP schema URL; selects the version (F2). |
| `schemaVersion` | string `"1.0"` | typed scalar | The value the selected schema accepts. |
| `proteome` | string | string | Required. The protein set name. |
| `sourceType` | enum string | string | Required: `predicted`, `database` or `mixed`. |
| `taxon` | object | one item scope | `name` and `uri` strings. |
| `version` | string | string | The protein set's own version. |
| `metadataAuthor` | array of object | array container | Ordered; each item is an `Author` object (F3). |
| `dateCreated` | date string | string | |
| `derivedFrom` | array of object | array container | Parent files by checksum; nested `accessionID` (F4). |
| `source` | array of object | array container | Asserted non-FAIR sources; `name` required (F4). |
| `geneticCode` | integer | typed integer | NCBI translation table ID. |
| `isoformPolicy` | enum string | string | `all`, `longestPerGene`, `canonicalPerGene`. |
| `predictionSoftware` | array of object | array container | Structured software (F5). |
| `predictionProtocol` | uri string | string | |
| `sequenceStats` | object | one item scope | Single object, not an array; integer counts (F6). |
| `completeness` | object | one item scope | Single BUSCO object (F6). |
| `voucherSpecimen` | string | string | |
| `accessionID` | object | one item scope | `name` and `url` strings. |
| `scholarlyArticle` | string | string | DOI. |
| `documentation` | string | string | |
| `identifier` | array of string | array container | |
| `relatedLink` | array of uri strings | array container | |
| `funding` | string | string | |
| `reuseConditions` | string | string | |
| `checksum` | string | string | An ordinary metadata value; see "Validity and verification". |

The optional core fields keep their FHR meaning. Genome-only FHR fields are absent by
construction.

## Nested objects and ordered arrays

- [F3] `metadataAuthor` is an **ordered array** of `Author` objects. Order is preserved.
  A single author is still a one-item array, never a bare object. Each item is a nested
  item scope (`data-fhr-type="object"`); the released v0.4 core adds the optional
  `nameType` property to `Author`, which is read as an ordinary property when the selected
  schema defines it.
- [F4] `source` and `derivedFrom` are arrays of independent nested objects. Each item is
  its own item scope; order is preserved; a single source is still a one-item array; an
  empty array is written as an empty array container and is distinct from an omitted
  property. A `derivedFrom` item's `accessionID` is a further nested item scope.
  `source` describes an asserted origin and `derivedFrom` a parent **file** identified by
  its FHR-family checksum; they are not interchangeable.
- [F5] `predictionSoftware` is an ordered array of `Software` objects:
  `name` (required), optional `version` and `uri`, and optional `commandLineOption`, an
  **ordered array of strings**. Command-line strings are data and are never executed;
  they may contain shell or markup characters, which are escaped in the HTML (F7).

## Statistics and completeness maps

- [F6] `sequenceStats` and `completeness` are **single** objects, each one item scope.
  They are not arrays, and repeating either one is invalid. Their members are scalars:
  `sequenceStats` has the integer counts `sequenceCount`, `geneCount` and `totalResidues`;
  `completeness` has `lineageDataset` and the counts `completeSingle`, `completeDuplicated`,
  `fragmented`, `missing` and `total`, with optional `buscoVersion` and `mode`. The
  schema's own requiredness and ranges apply.

## Zero, false, absence and escaping

- [F7] A property that is present with the value `0` is a value, and is kept. It is not
  the same as an omitted property, and a reader must not drop it or rewrite it as absent.
  The same holds for an empty array: `identifier: []` is present.
- FHP 1.0 defines no boolean property. If one is added, `false` is a value
  and `data-fhr-type="boolean"` keeps it; absence is omission only.
- Text and attribute values are escaped and decoded once, exactly as M2 and M3 require.
  Unicode, whitespace and character references round-trip unchanged. `data-fhr-type`
  keeps a number-like string a string, and keeps a typed `integer`, `number`, `boolean` or
  `null` exact.
- Script content and event-handler attributes are inert data: a reader never executes
  them and never takes metadata from them. A document whose metadata exists only inside a
  `<script>` block, a handler or another non-rendered place is not valid FHP microdata.
  Publishing or copying a page through another tool is not evidence that its microdata
  survives.
- A `<template>` element's contents are inert too: they create no item scope and no
  property, and they are excluded from text values. A record wrapped in `<template>` is
  therefore not an FHP item at all, and a property inside one contributes nothing.

## Repeated properties

Repeating a property is read as a list, following M4. A repeated field that takes a single
value (`proteome`, `schemaVersion`, `taxon`, `sequenceStats`, `completeness`, `checksum`
and the other scalars and single objects) is therefore invalid, and so is a repeated
array container. Only a single array container is unwrapped to its items; if the same
container appears twice, the occurrences stay as nested lists so schema validation can
reject them rather than silently flattening them into one list. Ordinary repeated
properties, including repeated untyped occurrences of an array field, still form one flat
list. The extracted metadata must validate against the selected FHP schema.

## Validity and verification

Reading and validating FHP microdata establishes **structural and schema validity only**:
the document has one FHP item scope, its values follow the binding, and the extracted
metadata matches the selected FHP schema. It does not establish that the metadata belongs
to any particular protein file.

In HTML the `checksum` property is an ordinary metadata value. HTML has no
checksum-coverage rule (the checksum rules R1 to R10 cover the FASTA/GFA/GFF3 containers),
so reading or validating microdata does **not** recompute or verify a SHA-512/256 over
the protein FASTA bytes. Exporting or copying metadata alone is not verification.

File-backed checks remain separate toolkit actions ([FHP.md](FHP.md)):

- `bioheaders verify` recomputes the SHA-512/256 over the file's exact bytes and compares
  it with the recorded `checksum`.
- `bioheaders verify-links` compares each `derivedFrom` parent checksum with the parent
  file on disk and reports, per parent, `matched`, `not matched` or `not checked`. A match
  establishes file identity, not that the translations are correct.
- A `source` entry, and any `assemblyAccession` a source states, cannot be verified this
  way at all; they stay assertions.

## Examples and tests

The binding is exercised by standalone HTML examples paired with their canonical records,
and by a test-only reader and writer:

| HTML | Canonical record |
| --- | --- |
| [`examples/fhp/minimal-predicted.microdata.fhp.html`](../examples/fhp/minimal-predicted.microdata.fhp.html) | [`minimal-predicted.fhp.json`](../examples/fhp/minimal-predicted.fhp.json) |
| [`examples/fhp/rich-microdata.microdata.fhp.html`](../examples/fhp/rich-microdata.microdata.fhp.html) | [`rich-microdata.fhp.json`](../examples/fhp/rich-microdata.fhp.json) |

The rich record covers nested `source` and `derivedFrom` (with a nested `accessionID`),
ordered author and software arrays, `sequenceStats` and `completeness` with a zero count,
and escaped Unicode and markup. Negative fixtures under `examples/fhp/` cover the wrong
itemtype, an unsupported version, malformed nesting, a repeated scalar and script-only
content.

`tests/fhp_microdata.py` is a **test-only** reader and writer built on the standard
library `html.parser`. It implements this binding and the shared rules M1 to M4 and R9;
it is not shipped and is not a runtime parser. `tests/test_fhp_microdata.py` checks that
the fixtures extract back to their canonical records, that the writer reproduces the
committed fixtures, and that the negative fixtures are rejected.

The rule ids F1 to F7 are stable labels local to this document. They add no requirements
beyond the text above and are not part of the shared conformance manifest, which covers
the R, M, J, P and G rules.

## What remains outside this document

- **Toolkit reader and writer**: implemented in
  [FAIR-bioHeaders-Tools#98](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools/pull/98)
  (for [FAIR-bioHeaders-Tools#58](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Tools/issues/58)),
  shipping in the first toolkit release that includes it. Until then, released toolkits
  still refuse FHP microdata output.
- **Website binding**: fair-bioheaders.github.io#21, with the family builder in #15. The
  released FHP form and readable tables added by website PR #27 stay microdata-free until
  this contract is published and the toolkit reader exists.
- **Publication**: this draft must be reviewed and published through
  FAIR-bioHeaders-Specification before any of the above treats it as adopted.
