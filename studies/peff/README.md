# PEFF placement probes (FHP #20)

These are deliberately synthetic experimental files, **not** family conformance
vectors, biological pilot data, an adopted hybrid syntax, or a converter. The
human taxon is an illustrative metadata value; the invented amino-acid strings
are not human protein claims. All metadata and experiment code authored here
are covered by this repository's March-2025-onward MPL-2.0 contribution terms.
No external parser source, ontology or specification PDF is vendored.

`generate.py` uses released fair-bioheaders **0.11.0**'s writer to compute each
FHP checksum, including experimental leading PEFF bytes. Eight fixtures retain
the exact record bytes of `plain.faa`; `fhp-tampered.faa` is the explicit negative
control that changes one residue without updating its checksum. `fixtures.json`
records the byte sizes/digests and toolkit checksum measurements. A toolkit
checksum measurement on the tampered fixture is not its asserted header value.

`run.py` captures all subprocess exit codes and diagnostics in `results.json`.
It uses Pyteomics **5.0**, the PSI-linked Perl validator snapshot identified by
archive SHA-256, and Comet at the exact source commit in `sources.json`.
Temporary index files stay outside this checkout. Its Comet index decoder is
intentionally restricted to the pinned v5 little-endian 64-bit layout; it
checks the footer/table boundaries. Peptide-table equality includes sequence,
flanking residues, mass and modification filter. It does not claim to validate
PEFF or test spectral searches. The changed-residue control produces a different
table, while all eight other placements/PEFF controls yield the same ten entries.
That makes the Comet column a payload check, not a placement check: Comet's
index ignores the header lines in every placement, so identical tables show the
protein records survived, and cannot tell one FHP/PEFF placement from another.
The validator's invalid-result exit 0 and Pyteomics' silent metadata loss are
preserved in the raw evidence, rather than converted into success booleans.

## Reproduce

Use a disposable environment. Versions, source digests, byte sizes and the
measured platform are recorded in `sources.json` and `results.json`; binary
Comet hashes are build-specific. The measured run used Python 3.15 on macOS.
The probe scripts use Python 3.9-compatible syntax. Network downloads/builds are
explicit preparation steps, not actions performed by the test suite. Work in a
directory of your own, not a shared temporary directory, and run the steps from
the repository root:

```sh
STUDY="$HOME/fhp-peff-study"   # any private, empty directory
mkdir -p "$STUDY"
# Portable SHA-256 check: GNU coreutils sha256sum, or shasum on macOS/BSD.
check_sha256() { # usage: check_sha256 DIGEST FILE
  if command -v sha256sum >/dev/null 2>&1; then
    printf '%s  %s\n' "$1" "$2" | sha256sum -c -
  else
    printf '%s  %s\n' "$1" "$2" | shasum -a 256 -c -
  fi
}

# Python packages: every distribution pinned by hash (pip refuses anything else).
python3 -m venv "$STUDY/env"
"$STUDY/env/bin/python" -m pip install --require-hashes -r studies/peff/requirements.txt

# Comet at the pinned commit; run.py refuses a binary outside a clean checkout of it.
git clone https://github.com/UWPR/Comet.git "$STUDY/comet"
git -C "$STUDY/comet" checkout c990672cfd1aebb5b65a475731a0f4790dff5c77
make -C "$STUDY/comet" -j4

# PSI validator archive; run.py re-checks this digest and extracts it itself.
curl --fail --location https://peptideatlas.org/export/PEFF/ProteomicsPEFF.zip \
  -o "$STUDY/ProteomicsPEFF.zip"
check_sha256 85e43373d5c377e46e36826561ade4f7ffa8b2c39bc036a9ab1ef0b531f34891 "$STUDY/ProteomicsPEFF.zip"

# The validator's one non-core Perl module, JSON 4.11, from its CPAN tarball by digest.
curl --fail --location https://cpan.metacpan.org/authors/id/I/IS/ISHIGAKI/JSON-4.11.tar.gz \
  -o "$STUDY/JSON-4.11.tar.gz"
check_sha256 713bdbe724dbb915ed50265ffe47e079a511980cb2427aa19076788bb64c3182 "$STUDY/JSON-4.11.tar.gz"
tar -xzf "$STUDY/JSON-4.11.tar.gz" -C "$STUDY"
(cd "$STUDY/JSON-4.11" && perl Makefile.PL INSTALL_BASE="$STUDY/perl5" && make && make install)

"$STUDY/env/bin/python" studies/peff/generate.py
PATH="$STUDY/env/bin:$PATH" PERL5LIB="$STUDY/perl5/lib/perl5" \
  "$STUDY/env/bin/python" studies/peff/run.py \
  --validator-archive "$STUDY/ProteomicsPEFF.zip" --comet "$STUDY/comet/comet.exe" \
  --output "$STUDY/peff-results.json"
python3 -m unittest discover -s tests -p 'test_peff_study.py' -v
```

`run.py` checks every pin **before** it executes anything external: the
installed Python sources against `sources.json`, the validator archive's size and
SHA-256 (it then extracts the archive itself into a private temporary directory
and checks `validatePEFF` and `PSI-MOD.obo` against `validatorFiles`), the Perl
`JSON` module version, and that the Comet binary sits in a checkout whose `HEAD`
is the pinned commit with no tracked-file changes. Pass `--comet-sha256` to also
require one exact Comet build when rerunning on the same machine. The committed
`results.json` was measured on 2026-11-16, before the Perl module pin, and does
not record its `JSON` version; a run under this recipe records it under
`perlModules`. A rerun of this recipe on Linux x86-64 (Python 3.13, Perl 5.40,
JSON 4.11) on 2026-11-18 reproduced every `cases` observation in the committed
`results.json` exactly; only the build-specific Comet binary digest differed.

Compare the new `cases` results with committed `results.json`; differences in
platform/build hashes are expected across machines, while changed reader
observations require investigation.

Check archive and installed source digests against `sources.json` before treating
another run as a reproduction. If an upstream URL changes bytes, stop and report
the difference. Comet parameters are generated by the pinned binary with `-p -q`,
then `peff_format` is set to 1, `peff_obo` to the pinned PSI-MOD file, and the
example spectral-library filename is cleared. The complete normalized parameter
text is captured in results. All other generated defaults are retained.
The fixture extension `.faa` lets the FHP CLI select FASTA; PEFF is recognized
from content, not a suffix. No online validation/upload is part of this recipe.

The regular unit suite checks committed fixture integrity, independent byte
checksums, preserved protein payloads, and the positive/negative observations.
It requires neither downloads, external tools, nor the optional experiment
packages. See [the findings and crosswalk](../../docs/FHP-PEFF.md).
