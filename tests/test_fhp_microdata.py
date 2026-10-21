# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The draft FHP HTML microdata binding (docs/FHP-MICRODATA.md).

The reader and writer live in ``tests/fhp_microdata.py``: they are test-only.
The runtime reader and writer remain toolkit work (FAIR-bioHeaders-Tools#58),
and the website binding (fair-bioheaders.github.io#21) and family builder
(fair-bioheaders.github.io#15) are coordinated, not shipped here.
"""

import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import fhp_microdata  # noqa: E402

FHP_ITEMTYPE = fhp_microdata.FHP_ITEMTYPE
FHR_ITEMTYPE = (
    "https://raw.githubusercontent.com/FAIR-bioHeaders/"
    "FAIR-bioHeaders-Specification/main/fhr.json"
)
EXAMPLES = ROOT / "examples" / "fhp"
SCHEMA = json.loads((ROOT / "fhp.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

# The committed valid HTML fixtures and the canonical record each one pins.
VALID_FIXTURES = {
    "minimal-predicted.microdata.fhp.html": "minimal-predicted.fhp.json",
    "rich-microdata.microdata.fhp.html": "rich-microdata.fhp.json",
}
NEGATIVE_FIXTURES = [
    "invalid-itemtype.microdata.fhp.html",
    "invalid-unsupported-version.microdata.fhp.html",
    "invalid-malformed-nesting.microdata.fhp.html",
    "invalid-repeated-scalar.microdata.fhp.html",
    "invalid-unsafe-content.microdata.fhp.html",
]


def load_record(name):
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    return json.loads(text) if name.endswith(".json") else yaml.safe_load(text)


def same_json(left, right):
    """JSON equality that keeps booleans, numbers, strings and containers apart."""
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same_json(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(map(same_json, left, right))
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def read_fixture(name):
    """Extract a fixture without validating it against the schema."""
    return fhp_microdata.read_page((EXAMPLES / name).read_text(encoding="utf-8"), SCHEMA)


def extract_page(page):
    """Read a document and reject it unless it also matches fhp.json (M4)."""
    record = fhp_microdata.read_page(page, SCHEMA)
    errors = list(VALIDATOR.iter_errors(record))
    if errors:
        raise fhp_microdata.MicrodataError(
            f"{errors[0].json_path}: {errors[0].message}")
    return record


def extract(name):
    """Read a fixture and reject it unless it also matches fhp.json (M4)."""
    return extract_page((EXAMPLES / name).read_text(encoding="utf-8"))


class FHPMicrodataFixtureTests(unittest.TestCase):
    def test_valid_fixtures_extract_to_their_canonical_records(self):
        for html, record_name in VALID_FIXTURES.items():
            with self.subTest(fixture=html):
                expected = load_record(record_name)
                self.assertTrue(same_json(read_fixture(html), expected))
                self.assertEqual(list(VALIDATOR.iter_errors(expected)), [])

    def test_committed_fixtures_are_the_writer_output(self):
        for html, record_name in VALID_FIXTURES.items():
            with self.subTest(fixture=html):
                expected = fhp_microdata.write_page(load_record(record_name))
                self.assertEqual((EXAMPLES / html).read_text(encoding="utf-8"), expected)

    def test_negative_fixtures_are_rejected(self):
        for name in NEGATIVE_FIXTURES:
            with self.subTest(fixture=name):
                with self.assertRaises(fhp_microdata.MicrodataError):
                    extract(name)

    def test_every_example_record_round_trips_through_the_writer(self):
        records = sorted(path for path in EXAMPLES.glob("*.fhp.*")
                         if path.suffix in {".json", ".yaml"})
        self.assertEqual(len(records), 7)
        for path in records:
            with self.subTest(example=path.name):
                record = load_record(path.name)
                recovered = fhp_microdata.read_page(
                    fhp_microdata.write_page(record), SCHEMA)
                self.assertTrue(same_json(recovered, record))


class FHPMicrodataBindingTests(unittest.TestCase):
    def minimal(self):
        return load_record("minimal-predicted.fhp.json")

    def test_record_scope_uses_the_fhp_itemtype(self):
        page = fhp_microdata.write_page(self.minimal())
        self.assertIn(f'itemtype="{FHP_ITEMTYPE}"', page)
        self.assertNotIn(FHR_ITEMTYPE, page)
        # The itemtype is the raw-main FHP schema URL, distinct from the
        # versioned/raw `schema` value the record itself carries.
        self.assertNotEqual(FHP_ITEMTYPE, self.minimal()["schema"])

    def test_fhr_itemtype_is_not_an_fhp_document(self):
        page = fhp_microdata.write_page(self.minimal(), itemtype=FHR_ITEMTYPE)
        with self.assertRaises(fhp_microdata.MicrodataError):
            fhp_microdata.read_page(page, SCHEMA)

    def test_two_fhp_scopes_are_rejected(self):
        page = fhp_microdata.write_page(self.minimal())
        scope = page[page.index("<div "):page.index("</div>") + len("</div>")]
        page = page.replace("</body>", scope + "</body>", 1)
        with self.assertRaises(fhp_microdata.MicrodataError):
            fhp_microdata.read_page(page, SCHEMA)

    def test_schema_property_selects_an_fhp_contract(self):
        record = dict(self.minimal(),
                      schema="https://raw.githubusercontent.com/FAIR-bioHeaders/"
                             "FAIR-bioHeaders-Specification/v0.4.0/fhp.json")
        self.assertEqual(list(VALIDATOR.iter_errors(record)), [])
        self.assertTrue(same_json(
            fhp_microdata.read_page(fhp_microdata.write_page(record), SCHEMA), record))
        # A w3id release URL is also an FHP selection.
        record["schema"] = "https://w3id.org/fair-bioheaders/fhp/v0.4.0"
        self.assertTrue(same_json(
            fhp_microdata.read_page(fhp_microdata.write_page(record), SCHEMA), record))

    def test_an_fhr_schema_value_is_not_an_fhp_record(self):
        record = dict(self.minimal(), schema=FHR_ITEMTYPE)
        with self.assertRaises(fhp_microdata.MicrodataError):
            fhp_microdata.read_page(fhp_microdata.write_page(record), SCHEMA)

    def test_a_non_release_ref_is_unsupported(self):
        # V4: a raw URL naming any ref other than main or a release tag is
        # unsupported-version, not a fallback to another schema.
        record = dict(self.minimal(),
                      schema="https://raw.githubusercontent.com/FAIR-bioHeaders/"
                             "FAIR-bioHeaders-Specification/0123abc/fhp.json")
        with self.assertRaises(fhp_microdata.MicrodataError):
            fhp_microdata.read_page(fhp_microdata.write_page(record), SCHEMA)

    def test_unsupported_version_is_rejected(self):
        record = dict(self.minimal(), schemaVersion=2)
        page = fhp_microdata.write_page(record)
        # Structurally the document is fine; the selected schema does not accept
        # its schemaVersion, and the reader must not check another schema.
        self.assertTrue(same_json(fhp_microdata.read_page(page, SCHEMA), record))
        with self.assertRaises(fhp_microdata.MicrodataError):
            extract_page(page)

    def test_repeated_scalar_property_becomes_a_list(self):
        page = fhp_microdata.write_page(self.minimal()).replace(
            "</div>",
            '<span itemprop="proteome" data-fhr-type="string">Second</span></div>', 1)
        extracted = fhp_microdata.read_page(page, SCHEMA)
        self.assertEqual(extracted["proteome"],
                         [self.minimal()["proteome"], "Second"])
        self.assertTrue(list(VALIDATOR.iter_errors(extracted)))

    def test_malformed_array_child_is_rejected(self):
        page = fhp_microdata.write_page(self.minimal()).replace(
            'itemprop="item" itemscope', 'itemprop="author" itemscope', 1)
        with self.assertRaises(fhp_microdata.MicrodataError):
            fhp_microdata.read_page(page, SCHEMA)

    def test_object_without_itemscope_is_rejected(self):
        page = fhp_microdata.write_page(self.minimal()).replace(
            '<span itemprop="taxon" itemscope', '<span itemprop="taxon"', 1)
        with self.assertRaises(fhp_microdata.MicrodataError):
            fhp_microdata.read_page(page, SCHEMA)

    def test_nested_unrelated_scope_does_not_leak_properties(self):
        page = fhp_microdata.write_page(self.minimal()).replace(
            "</div>",
            '<div itemscope><span itemprop="proteome">Leaked</span></div></div>', 1)
        self.assertTrue(same_json(fhp_microdata.read_page(page, SCHEMA), self.minimal()))

    def test_zero_is_a_value_and_absence_is_omission(self):
        rich = read_fixture("rich-microdata.microdata.fhp.html")
        self.assertEqual(rich["source"][0]["sequenceCount"], 0)
        self.assertIn("sequenceCount", rich["source"][0])
        self.assertNotIn("source", self.minimal())
        # An empty array is present and distinct from an omitted list.
        record = dict(self.minimal(), identifier=[])
        self.assertTrue(same_json(
            fhp_microdata.read_page(fhp_microdata.write_page(record), SCHEMA), record))

    def test_false_is_a_value_not_absence(self):
        # FHP schemaVersion 1 defines no boolean property; the typed form keeps
        # a false value when one is added. The reader must not drop it.
        self.assertIs(fhp_microdata._parse_typed("false", "boolean"), False)
        page = fhp_microdata.write_page(self.minimal()).replace(
            "</div>",
            '<span itemprop="newFlag" data-fhr-type="boolean">false</span></div>', 1)
        extracted = fhp_microdata.read_page(page, SCHEMA)
        self.assertIs(extracted["newFlag"], False)

    def test_ordered_arrays_keep_their_order(self):
        rich = read_fixture("rich-microdata.microdata.fhp.html")
        self.assertEqual([author["name"] for author in rich["metadataAuthor"]],
                         ["Synthetic first author (placeholder)",
                          "Synthetic second author (placeholder)"])
        self.assertEqual(rich["predictionSoftware"][0]["commandLineOption"],
                         ["--species", "human", "--flag=<script>"])
        self.assertEqual([parent["headerType"] for parent in rich["derivedFrom"]],
                         ["FHR", "FHGFF3"])

    def test_nested_sources_and_parents(self):
        rich = read_fixture("rich-microdata.microdata.fhp.html")
        self.assertEqual(rich["derivedFrom"][1]["accessionID"],
                         {"name": "Synthetic annotation (placeholder)"})
        self.assertEqual(rich["source"][0]["name"],
                         "Synthetic database source (placeholder)")
        self.assertEqual(rich["sequenceStats"],
                         {"sequenceCount": 20000, "geneCount": 20000,
                          "totalResidues": 11000000})
        self.assertEqual(rich["completeness"]["completeDuplicated"], 0)

    def test_escaped_unicode_and_markup_round_trip_as_data(self):
        rich = read_fixture("rich-microdata.microdata.fhp.html")
        self.assertIn("café", rich["proteome"])
        self.assertIn("<script>alert(1)</script>", rich["documentation"])
        self.assertIn("&", rich["documentation"])
        self.assertIn("測試", rich["documentation"])
        # The writer escapes markup, so the committed page never contains an
        # executable script from a value.
        page = (EXAMPLES / "rich-microdata.microdata.fhp.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_script_and_handler_content_is_never_metadata(self):
        page = fhp_microdata.write_page(self.minimal()).replace(
            '<span itemprop="checksum" data-fhr-type="string">'
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=</span>",
            '<script>document.getElementById("x").textContent="A";</script>', 1)
        extracted = fhp_microdata.read_page(page, SCHEMA)
        self.assertNotIn("checksum", extracted)
        self.assertTrue(list(VALIDATOR.iter_errors(extracted)))

    def test_first_attribute_wins(self):
        page = fhp_microdata.write_page(self.minimal()).replace(
            '<span itemprop="proteome" data-fhr-type="string">',
            '<span itemprop="proteome" itemprop="notAField" data-fhr-type="string">', 1)
        extracted = fhp_microdata.read_page(page, SCHEMA)
        self.assertNotIn("notAField", extracted)
        self.assertEqual(extracted["proteome"], self.minimal()["proteome"])


if __name__ == "__main__":
    unittest.main()
