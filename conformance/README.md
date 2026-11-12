# FHP-owned conformance vectors

This package is **FHP-owned** (the Q4 decision of
[issue #2](https://github.com/FAIR-bioHeaders/FHP-Specification/issues/2),
recorded 2026-11-12, in
[docs/DEVELOPMENT-TREE.md](../docs/DEVELOPMENT-TREE.md)): one manifest for
this repository's own purposes. It covers the complete `fhp-fasta` vector set
of the shared v0.5.0 line — protein FASTA files with an FHP header, applying
the shared header and checksum rules ([docs/FORMAT.md](../docs/FORMAT.md)) and
the FHP schema rules P1 and P2 ([docs/FHP.md](../docs/FHP.md#rules)), the
extension-field rule R15 and the schema-selection rules V1, V2 and V4
([docs/SCHEMA-VERSIONS.md](../docs/SCHEMA-VERSIONS.md)) — plus the shared
`fasta-*.fhr.fasta` vectors, which exercise the R rules on the same FASTA
header reader this repository's readers must satisfy. Every `fhp-fasta` file
except `fhp-fasta-author-bad-name-type` (this repository's own addition) is a
byte-for-byte copy of the shared published vector at the pinned release
commit, digested in [`provenance.json`](../provenance.json) and verified by
`scripts/check_shared_parity.py`.

The **complete family manifest** — the GFA, microdata, JSON-LD and FHGFF3
vectors and all 40 rules — is not maintained here. It runs in full from the
pinned shared tree in the `shared-conformance` job of
[`.github/workflows/shared-parity.yml`](../.github/workflows/shared-parity.yml).
The remaining non-FASTA vector files in `valid/` and `invalid/` are frozen
pre-v0.5.0 family copies kept as history (`provenance.json` `legacy`); the
local generator and checker do not read them.

## Layout

- `valid/`: files that a conforming implementation must accept.
- `invalid/`: files that it must reject.
- `manifest.json`: the expected outcome for every FHP-owned vector.
- `*.gz`: gzip or BGZF copies. Validate their decompressed bytes.

Every file is byte-exact. `.gitattributes` turns off line-ending conversion for
this directory, so CR and CRLF vectors stay unchanged in every checkout. Don't
open and re-save them in an editor. Run the generator instead
(`python scripts/make_conformance.py`); it regenerates only the FHP-owned
files and the manifest.

## Manifest

`rules` maps each stable rule id to a short summary: R1 to R15 from
docs/FORMAT.md, M1 to M4 from docs/MICRODATA.md, J1 to J7 from
docs/JSONLD.md, P1 to P2 from docs/FHP.md, G1 to G3 from docs/FHGFF3.md and
V1 to V6 from docs/SCHEMA-VERSIONS.md — the ids must equal the bracketed
tokens in those documents. Rules that the FHP-owned vectors do not exercise
in both directions carry a `notApplicable` note: R11 and R14 are
recommendations (validators warn, they do not reject), J7 and J8 constrain
writers, and the remaining notes point at the family manifest in the pinned
shared tree, which tests those rules' vectors.

Every entry in `vectors` has these fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable vector name |
| `file` | Path relative to this directory |
| `format` | `fasta` (genome FASTA with an FHR header) or `fhp-fasta` (protein FASTA with an FHP header) |
| `compressed` | `true` for gzip/BGZF files; `compression` then gives `gzip` or `bgzf` |
| `expected` | `valid` or `invalid` |
| `rules` | Valid vectors only: the rules the file exercises |
| `description` | Valid vectors only: what the file exercises |
| `checksum` | Valid vectors: the expected FHR/FHP checksum, base64 SHA-512/256 |
| `metadata` | Valid vectors: some expected parsed values (`genome`, `version`, `masking` for `fasta`; `proteome`, `version`, `sourceType` for `fhp-fasta`). The P1/P2 `fhp-fasta` vectors: the metadata they yield, which fails `fhp.json` (P1) or `fhr.json` (P2) |
| `rule` | Invalid vectors only: the rule the file breaks |
| `reason` | Invalid vectors only: how the file breaks that rule |
| `result` | Invalid vectors only, where set: the expected outcome class (`unsupported-version` for the V4 vector) |

An invalid vector breaks one rule and is otherwise correct. Where possible its
stated checksum matches the bytes, so an implementation can't pass by failing the
checksum comparison by accident. The R1, R3 and R4 vectors are the exception:
they deliberately carry a checksum computed the wrong way, or one made stale by
editing the file. Reasons describe the defect, not any implementation's error
message.

Compressed valid vectors decompress to the bytes of `fasta-lf` or
`fhp-fasta-lf` and keep their checksum: the digest covers the decompressed
bytes. JSON numbers compare by value, so `1` and `1.0` are equal, but strings,
numbers and booleans are never equal to each other. Valid metadata conforms to
`fhr.json` (`fasta`) or `fhp.json` (`fhp-fasta`). The checksums are
real; valid vectors carry no placeholder checksum or SeqCol value.

## Using the vectors in another implementation

For each manifest entry, read `file` and decompress it if `compressed` is true.
For a `valid` vector, your implementation must accept the file, compute
`checksum`, and parse the listed `metadata` values. For an `invalid` vector, it
must reject the file (a V4 vector rejects it with an unsupported-version
result). Reporting the rule id is optional. Treat any difference as
a bug in the implementation or the vectors, and report it as an issue.

Both vector formats go to a FASTA header reader — `fhr-fasta-validate` in the
`fair-bioheaders` toolkit:

```bash
python scripts/check_conformance.py --converter           # commands on PATH
python scripts/check_conformance.py --converter .venv     # a virtual environment
python scripts/check_conformance.py --skip-regeneration --require-format fhp-fasta --converter "$VENV"
```

## Regenerating and checking

`scripts/make_conformance.py` builds every FHP-owned vector from small
templates. It computes the checksums with Python's `hashlib` (`sha512_256`) and
`base64`, independently of the converter. It writes gzip and BGZF data as
stored deflate blocks with mtime 0 and no file name, so the output doesn't
depend on the local zlib build. Rerunning it reproduces identical bytes. The
`fhp-fasta` builders follow the shared v0.5.0 generator, so the regenerated
bytes stay equal to the pinned shared copies that `provenance.json` digests.

```bash
python scripts/make_conformance.py            # rewrite the FHP-owned vectors and manifest.json
python scripts/check_conformance.py           # standard library only
python scripts/check_conformance.py --schema  # also validate metadata (PyYAML, jsonschema)
```

`check_conformance.py` regenerates the FHP-owned vectors in a temporary
directory and compares the bytes (the frozen legacy family files on disk are
outside this comparison), checks that the manifest covers every rule in the
documents of `RULE_DOCUMENTS`, and recomputes each checksum with a separate
reading of the rules. CI runs these checks and then runs the pinned released
converter (`fair-bioheaders==0.9.0`) over every vector, requiring the
`fhp-fasta` format. To add a vector, edit the generator, rerun it, and commit
the script together with its output.
