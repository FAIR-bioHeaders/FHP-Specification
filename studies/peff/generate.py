# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Generate synthetic placement probes with fair-bioheaders 0.11.0 (not a converter)."""

import hashlib
import json
from pathlib import Path

from bioheaders import __version__, fhr
from bioheaders.cli import checksum, combined_header

ROOT = Path(__file__).parent
PAYLOAD = b">syn:p1 \\PName=Synthetic protein one \\Length=19\nMPEPTIDEKACDEFGHIKR\n>syn:p2 \\PName=Synthetic protein two \\Length=17\nMSTNPKPQRKTKRNTNR\n"
PEFF = b"# PEFF 1.0\n# //\n# DbName=Synthetic placement study\n# Prefix=syn\n# DbSource=https://example.org/synthetic\n# DbVersion=1\n# SequenceType=AA\n# NumberOfEntries=2\n# //\n"


def generate():
    if __version__ != "0.11.0":
        raise RuntimeError("Requires fair-bioheaders 0.11.0")
    data = fhr(
        schema="https://w3id.org/fair-bioheaders/fhp/v0.6.0",
        schemaVersion="1.2",
        proteome="Synthetic placement study (not biological data)",
        sourceType="database",
        taxon={
            "name": "Homo sapiens",
            "uri": "https://identifiers.org/taxonomy:9606",
        },
        version="1",
        metadataAuthor=[{"name": "Synthetic study fixture"}],
        dateCreated="2026-11-16",
        source=[{"name": "Synthetic fixture", "release": "1"}],
        checksum="A" * 43 + "=",
    )

    # The toolkit's writer computes the checksum over lead + header + body.
    def fhp(lead=b"", body=PAYLOAD):
        return lead + combined_header(data, [body], "fasta", lead) + body

    fixtures = {
        "plain.faa": PAYLOAD,
        "peff-only.faa": PEFF + PAYLOAD,
        "fhp-only.faa": fhp(),
        "fhp-before-peff.faa": fhp(body=PEFF + PAYLOAD),
        "peff-before-fhp.faa": fhp(lead=PEFF),
        "fhp-inside-peff.faa": fhp(lead=PEFF[:11], body=PEFF[11:] + PAYLOAD),
        "peff-missing-prefix.faa": PEFF.replace(b"# Prefix=syn\n", b"") + PAYLOAD,
        "peff-wrong-count.faa": PEFF.replace(b"Entries=2", b"Entries=3") + PAYLOAD,
    }
    fixtures["fhp-tampered.faa"] = fixtures["fhp-only.faa"].replace(
        b"MPEPTIDEK", b"APEPTIDEK"
    )
    return fixtures


if __name__ == "__main__":
    manifest = {}
    for name, content in generate().items():
        (ROOT / name).write_bytes(content)
        manifest[name] = {
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "toolkitChecksum": (
                checksum(content, "fasta") if b";~checksum:" in content else None
            ),
        }
    (ROOT / "fixtures.json").write_text(json.dumps(manifest, indent=2) + "\n")
