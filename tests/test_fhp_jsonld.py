# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The draft FHP JSON-LD context, vocabulary additions and round trip (issue #4).

FHP is a draft: runtime reader/writer support is coordinated with
FAIR-bioHeaders-Tools#58, and the context and terms are published through
FAIR-bioHeaders-Specification#107. The canonical JSON-LD here is loss-preserving
and distinct from the one-way schema.org export; it carries no export terms.

The reference writer and canonical reader are ``scripts/make_jsonld.py``. The
PyLD tests are skipped with a message when PyLD is not installed; nothing is
fetched from the network.
"""

import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import make_jsonld  # noqa: E402

try:
    from pyld import jsonld as pyld
except ImportError:  # pragma: no cover - depends on the environment
    pyld = None

SDO = "http://schema.org/"
FHR = "https://w3id.org/fair-bioheaders/terms#"
XSD = "http://www.w3.org/2001/XMLSchema#"
DCT = "http://purl.org/dc/terms/"
FHP_CONTEXT = ROOT / "jsonld" / "fhp.context.jsonld"
FHP_TERMS = ROOT / "jsonld" / "fhp.terms.ttl"
FHP_TERMS_JSONLD = ROOT / "jsonld" / "fhp.terms.jsonld"
# Scope name -> the fhp.json path whose object properties are the scope's keys.
NESTED = {
    "taxon": ("taxon",),
    "metadataAuthor": ("metadataAuthor", "[]"),
    "accessionID": ("accessionID",),
    "derivedFrom": ("derivedFrom", "[]"),
    "source": ("source", "[]"),
    "predictionSoftware": ("predictionSoftware", "[]"),
    "sequenceStats": ("sequenceStats",),
    "completeness": ("completeness",),
}
COUNTS = {"record": 25, "taxon": 2, "metadataAuthor": 2, "accessionID": 2, "derivedFrom": 5,
          "source": 7, "predictionSoftware": 4, "sequenceStats": 3, "completeness": 8}
# The FHP objects whose writer @type the tests expect (data-model section 5).
TYPES = {
    "record": {"Dataset"}, "taxon": {"Taxon"},
    "metadataAuthor": {"Person", "Organization", "Agent"}, "accessionID": {"PropertyValue"},
    "derivedFrom": {"DerivedFrom"}, "source": {"Source"},
    "predictionSoftware": {"SoftwareApplication"}, "sequenceStats": {"SequenceStats"},
    "completeness": {"Completeness"},
}
# The export terms are FHR-only: the FHP canonical context must not carry them.
EXPORT_TERMS = {"keywords", "url", "conformsTo"}
# fhr: terms the shared vocabulary already defines (owned by FHR), which FHP
# reuses with the same IRIs. Kept as a literal so a change is a visible review.
SHARED = {"Agent", "accessionID", "checksum", "commandLineOption", "metadataAuthor",
          "relatedLink", "schemaVersion", "seqcol_id", "voucherSpecimen"}
FHP_ADDED = {
    "Completeness", "DerivedFrom", "SequenceStats", "Source",
    "assemblyAccession", "buscoVersion", "completeDuplicated", "completeness",
    "completeSingle", "derivedFrom", "fragmented", "geneCount", "geneticCode",
    "headerType", "isoformPolicy", "lineageDataset", "missing", "mode",
    "predictionProtocol", "predictionSoftware", "relationship", "release",
    "sequenceCount", "sequenceStats", "setIdentifier", "source", "sourceType",
    "total", "totalResidues",
}
# The FHP term IRIs that schema.org already covers; the rest are fhr: terms.
SDO_TERMS = {"schema": "schemaVersion", "proteome": "name", "taxon": "about",
             "version": "version", "dateCreated": "dateCreated", "scholarlyArticle": "citation",
             "documentation": "description", "identifier": "identifier", "funding": "funding",
             "reuseConditions": "license"}


def resolve(node, document):
    while isinstance(node, dict) and "$ref" in node:
        target = document
        for part in node["$ref"][2:].split("/"):
            target = target[part]
        node = {**target, **{k: v for k, v in node.items() if k != "$ref"}}
    return node


def object_properties(node, document):
    node = resolve(node, document)
    if "properties" in node:
        return list(node["properties"])
    if "items" in node:
        return object_properties(node["items"], document)
    for option in node.get("anyOf", []):
        names = object_properties(option, document)
        if names:
            return names
    return []


def expand(value, scope):
    if isinstance(value, dict):
        value = value["@id"]
    if value.startswith("@") or "://" in value:
        return value
    prefix, _, local = value.partition(":")
    return scope[prefix] + local


def equal(left, right):
    """Key order ignored; array order and JSON types kept (data-model section 8)."""
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(map(equal, left, right))
    return type(left) is type(right) and left == right


def examples():
    found = {}
    for stem in make_jsonld.FHP_EXAMPLES:
        json_path = ROOT / "examples" / "fhp" / f"{stem}.fhp.json"
        yaml_path = ROOT / "examples" / "fhp" / f"{stem}.fhp.yaml"
        found[stem] = (json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists()
                       else yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    return found


def fhr_iris(node):
    """Every fhr: IRI used in a context document (CURIEs or full IRIs)."""
    found = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found |= fhr_iris(value)
    elif isinstance(node, list):
        for value in node:
            found |= fhr_iris(value)
    elif isinstance(node, str):
        if node.startswith("fhr:"):
            found.add(FHR + node[4:])
        elif node.startswith(FHR) and node != FHR:
            found.add(node)
    return found


class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "fhp.json").read_text())
        cls.document = json.loads(FHP_CONTEXT.read_text(encoding="utf-8"))
        cls.root = cls.document["@context"]
        cls.scopes = {"record": cls.root}
        for name in NESTED:
            cls.scopes[name] = cls.root[name]["@context"][1]
        cls.keys = {"record": list(cls.schema["properties"])}
        for name, path in NESTED.items():
            cls.keys[name] = object_properties(cls.schema["properties"][path[0]], cls.schema)

    def test_generated_files_are_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/make_jsonld.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_header_prefixes_and_no_export_terms(self):
        self.assertEqual(list(self.document), ["@context"])
        self.assertEqual(self.root["@version"], 1.1)
        self.assertIs(self.root["@protected"], True)
        self.assertEqual(self.root["sdo"], SDO)
        self.assertEqual(self.root["fhr"], FHR)
        self.assertEqual(self.root["xsd"], XSD)
        self.assertEqual(self.root["dct"], DCT)
        # The FHR export-context terms are root-level only; nested objects use
        # sdo:url legitimately (accessionID.url, source.url).
        self.assertFalse(EXPORT_TERMS & set(self.root))
        for name, scope in self.scopes.items():
            with self.subTest(scope=name):
                self.assertNotIn("@vocab", scope)
                self.assertNotIn("@base", scope)
                if name != "record":
                    self.assertNotIn("schema", scope)
        self.assertIsInstance(self.root["schema"], dict)  # A term, never a prefix.

    def test_every_fhp_key_is_a_term_in_its_scope(self):
        for name, count in COUNTS.items():
            with self.subTest(scope=name):
                self.assertEqual(len(self.keys[name]), count)
                for key in self.keys[name]:
                    self.assertIn(key, self.scopes[name])

    def test_terms_follow_fhp_json_order(self):
        for name, scope in self.scopes.items():
            with self.subTest(scope=name):
                terms = [key for key in scope if key in self.keys[name]]
                self.assertEqual(terms, self.keys[name])

    def test_only_documented_extra_terms(self):
        allowed = {"@version", "@protected", "sdo", "fhr", "xsd", "dct"}
        for name, scope in self.scopes.items():
            with self.subTest(scope=name):
                extra = set(scope) - set(self.keys[name]) - allowed
                expected = set(TYPES[name])
                if name == "record":
                    expected = expected | {"subjectOf"} | set().union(*TYPES.values())
                self.assertEqual(extra, expected)
                for term in TYPES[name]:
                    self.assertIsInstance(scope[term], str)

    def test_nested_scopes_reset_and_protect(self):
        for name in NESTED:
            with self.subTest(scope=name):
                value = self.root[name]["@context"]
                self.assertIsInstance(value, list)
                self.assertEqual(len(value), 2)
                self.assertIsNone(value[0])
                self.assertIs(value[1]["@protected"], True)
                self.assertEqual(value[1]["sdo"], SDO)
                self.assertEqual(value[1]["fhr"], FHR)
        self.assertEqual(self.root["metadataAuthor"]["@context"],
                         self.root["metadataAuthor"]["@context"])

    def test_injective_per_scope(self):
        for name, scope in self.scopes.items():
            with self.subTest(scope=name):
                seen = {}
                for key, value in scope.items():
                    if key.startswith("@") or key in {"sdo", "fhr", "xsd", "dct"}:
                        continue
                    iri = expand(value, {**self.root, **scope})
                    self.assertNotIn(iri, seen, f"{key} and {seen.get(iri)} share {iri}")
                    seen[iri] = key

    def test_shared_terms_keep_their_fhr_iri(self):
        """FHP reuses the shared vocabulary: the same slot name maps to the same IRI."""
        fhr_context = json.loads(
            (ROOT / "jsonld" / "fhr.context.jsonld").read_text(encoding="utf-8"))["@context"]
        for key in ("schemaVersion", "metadataAuthor", "accessionID", "relatedLink", "checksum",
                    "voucherSpecimen"):
            with self.subTest(key=key):
                self.assertEqual(expand(self.root[key], self.root),
                                 expand(fhr_context[key], fhr_context))
        self.assertEqual(expand(self.scopes["taxon"]["uri"], self.scopes["taxon"]), "@id")
        self.assertEqual(expand(self.scopes["accessionID"]["name"], self.scopes["accessionID"]),
                         SDO + "name")

    def test_fhp_specific_terms_use_the_family_namespace(self):
        for key in ("proteome", "sourceType", "source", "derivedFrom", "geneticCode",
                    "isoformPolicy", "predictionSoftware", "predictionProtocol",
                    "sequenceStats", "completeness"):
            with self.subTest(key=key):
                iri = expand(self.root[key], self.root)
                if key == "proteome":
                    self.assertEqual(iri, SDO + "name")
                else:
                    self.assertEqual(iri, FHR + key)
        node_types = {"source": ("Source", FHR), "derivedFrom": ("DerivedFrom", FHR),
                      "predictionSoftware": ("SoftwareApplication", SDO),
                      "sequenceStats": ("SequenceStats", FHR),
                      "completeness": ("Completeness", FHR)}
        for name, (key, namespace) in node_types.items():
            with self.subTest(scope=name):
                self.assertEqual(expand(self.scopes[name][key], self.scopes[name]),
                                 namespace + key)

    def test_serialisation(self):
        text = FHP_CONTEXT.read_text(encoding="utf-8")
        self.assertEqual(text, json.dumps(self.document, indent=2) + "\n")


class VocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rdflib import Graph, Namespace
        cls.Graph = Graph
        cls.FHR = Namespace(FHR)
        cls.fhr_graph = Graph().parse(ROOT / "jsonld" / "terms.ttl", format="turtle")
        cls.fhp_graph = Graph().parse(FHP_TERMS, format="turtle")
        cls.document = json.loads(FHP_CONTEXT.read_text(encoding="utf-8"))
        cls.text = FHP_TERMS.read_text(encoding="utf-8")

    def defined(self, graph, kind):
        from rdflib.namespace import RDF, RDFS
        return {str(s)[len(FHR):] for s in graph.subjects(RDF.type, kind)
                if str(s).startswith(FHR)}

    def test_additions_are_exactly_the_fhp_terms(self):
        from rdflib.namespace import RDF, RDFS
        classes = self.defined(self.fhp_graph, RDFS.Class)
        properties = self.defined(self.fhp_graph, RDF.Property)
        self.assertEqual(classes | properties, FHP_ADDED)

    def test_additions_do_not_redefine_shared_terms(self):
        from rdflib.namespace import RDF, RDFS
        shared = (self.defined(self.fhr_graph, RDFS.Class)
                  | self.defined(self.fhr_graph, RDF.Property))
        # The shared vocabulary is broader than the subset FHP reuses.
        self.assertLessEqual(SHARED, shared)
        fhp = self.defined(self.fhp_graph, RDFS.Class) | self.defined(self.fhp_graph, RDF.Property)
        self.assertEqual(shared & fhp, set())

    def test_every_fhr_iri_in_the_context_is_defined(self):
        used = fhr_iris(self.document)
        self.assertTrue(used)
        defined = {FHR + name for name in SHARED | FHP_ADDED}
        self.assertEqual(used - defined, set())

    def test_every_defined_term_is_used(self):
        used = {iri[len(FHR):] for iri in fhr_iris(self.document)}
        self.assertEqual(FHP_ADDED - used, set())

    def test_every_term_has_label_comment_and_definition(self):
        from rdflib import Literal, URIRef
        from rdflib.namespace import RDFS
        ontology = URIRef("https://w3id.org/fair-bioheaders/terms")
        for name in FHP_ADDED:
            term = self.FHR[name]
            with self.subTest(term=name):
                self.assertEqual(list(self.fhp_graph.objects(term, RDFS.label)),
                                 [Literal(name, lang="en")])
                comments = list(self.fhp_graph.objects(term, RDFS.comment))
                self.assertEqual(len(comments), 1)
                self.assertTrue(str(comments[0]).strip())
                self.assertEqual(list(self.fhp_graph.objects(term, RDFS.isDefinedBy)), [ontology])

    def test_jsonld_vocabulary_has_the_same_triples(self):
        from rdflib.compare import isomorphic
        other = self.Graph().parse(FHP_TERMS_JSONLD, format="json-ld")
        self.assertTrue(isomorphic(self.fhp_graph, other))

    def test_provenance_header(self):
        head = self.text.split("@prefix")[0]
        self.assertIn("Generated by scripts/make_jsonld.py", head)
        self.assertIn("do not edit", head)
        self.assertIn("FAIR-bioHeaders-Tools#58", head)
        self.assertIn("FAIR-bioHeaders-Specification#107", head)
        self.assertIn("owned by FHP development", head)
        for name in SHARED:
            self.assertIn(f"fhr:{name}", head)
        for name in FHP_ADDED:
            self.assertNotIn(f"#   fhr:{name}\n", head)


class WriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = examples()
        cls.context = json.loads(FHP_CONTEXT.read_text())["@context"]

    def test_writer_steps(self):
        for name, record in self.examples.items():
            with self.subTest(record=name):
                document = make_jsonld.fhp_to_jsonld(record)
                self.assertEqual(list(document)[:2], ["@context", "@type"])
                self.assertEqual(document["@context"], self.context)
                self.assertEqual(document["@type"], "Dataset")
                self.assertEqual(list(document)[2:], list(record))
                for key, kind in make_jsonld.FHP_NODE_TYPES.items():
                    if isinstance(record.get(key), dict):
                        self.assertEqual(document[key]["@type"], kind)
                for key, kind in make_jsonld.FHP_LIST_TYPES.items():
                    for item in document.get(key, []):
                        if isinstance(item, dict):
                            self.assertEqual(item["@type"], kind)
                for item in document.get("metadataAuthor", []):
                    orcid = str(item.get("uri", "")).startswith("https://orcid.org/")
                    self.assertEqual(item["@type"], "Person" if orcid else "Agent")

    def test_canonical_round_trip(self):
        for name, record in self.examples.items():
            with self.subTest(record=name):
                document = json.loads(json.dumps(make_jsonld.fhp_to_jsonld(record)))
                self.assertTrue(equal(make_jsonld.fhp_canonical_record(document), record))

    def test_ordered_authors_and_nested_objects_are_preserved(self):
        record = copy.deepcopy(self.examples["rich-predicted"])
        record["metadataAuthor"] = [
            {"name": "First author (placeholder)"},
            {"name": "Second author (placeholder)", "uri": "https://orcid.org/0000-0002-1825-0097"},
            {"name": "Third author (placeholder)"},
        ]
        document = make_jsonld.fhp_to_jsonld(record)
        self.assertEqual([item["name"] for item in document["metadataAuthor"]],
                         [item["name"] for item in record["metadataAuthor"]])
        back = make_jsonld.fhp_canonical_record(json.loads(json.dumps(document)))
        self.assertEqual([item["name"] for item in back["metadataAuthor"]],
                         [item["name"] for item in record["metadataAuthor"]])
        self.assertTrue(equal(back, record))
        self.assertEqual([item["headerType"] for item in back["derivedFrom"]],
                         [item["headerType"] for item in record["derivedFrom"]])

    def test_scalar_types_are_preserved(self):
        record = self.examples["rich-predicted"]
        document = json.loads(json.dumps(make_jsonld.fhp_to_jsonld(record)))
        self.assertIsInstance(document["schemaVersion"], int)
        self.assertIsInstance(document["geneticCode"], int)
        self.assertIsInstance(document["sequenceStats"]["sequenceCount"], int)
        back = make_jsonld.fhp_canonical_record(document)
        self.assertIsInstance(back["schemaVersion"], int)
        self.assertIsInstance(back["geneticCode"], int)
        self.assertIsInstance(back["sequenceStats"]["totalResidues"], int)

    def test_absent_optional_fields_stay_absent(self):
        minimal = self.examples["minimal-predicted"]
        document = make_jsonld.fhp_to_jsonld(minimal)
        self.assertEqual(set(document) - {"@context", "@type"}, set(minimal))
        for key in ("source", "derivedFrom", "completeness", "sequenceStats"):
            self.assertNotIn(key, document)

    def test_source_relationships_are_preserved(self):
        record = self.examples["rich-mixed"]
        document = make_jsonld.fhp_to_jsonld(record)
        back = make_jsonld.fhp_canonical_record(json.loads(json.dumps(document)))
        self.assertEqual([item["name"] for item in back["source"]],
                         [item["name"] for item in record["source"]])
        self.assertEqual([item["relationship"] for item in back["derivedFrom"]],
                         [item["relationship"] for item in record["derivedFrom"]])
        self.assertEqual(back["sourceType"], record["sourceType"])

    def test_fixtures_are_writer_output(self):
        for stem in make_jsonld.FHP_EXAMPLES:
            with self.subTest(example=stem):
                record = self.examples[stem]
                text = (ROOT / "examples" / "fhp" / f"{stem}.fhp.jsonld").read_text(
                    encoding="utf-8")
                self.assertEqual(text, make_jsonld.fhp_jsonld_text(record))

    def test_documentation_url_becomes_subject_of(self):
        record = dict(self.examples["minimal-predicted"],
                      documentation="https://example.org/proteome/README")
        document = make_jsonld.fhp_to_jsonld(record)
        self.assertNotIn("documentation", document)
        self.assertEqual(document["subjectOf"], record["documentation"])
        back = make_jsonld.fhp_canonical_record(json.loads(json.dumps(document)))
        self.assertTrue(equal(back, record))


class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = examples()["rich-predicted"]
        cls.document = make_jsonld.fhp_to_jsonld(cls.record)

    def test_unknown_context_is_rejected(self):
        for context in ("https://schema.org/",
                        "https://example.org/unknown.jsonld",
                        "https://raw.githubusercontent.com/FAIR-bioHeaders/"
                        "FAIR-bioHeaders-Specification/main/jsonld/fhr.context.jsonld"):
            with self.subTest(context=context):
                document = dict(self.document, **{"@context": context})
                with self.assertRaisesRegex(ValueError, "FHP"):
                    make_jsonld.fhp_canonical_record(document)

    def test_embedded_fhr_context_is_rejected(self):
        document = dict(self.document,
                        **{"@context": json.loads(
                            (ROOT / "jsonld" / "fhr.context.jsonld").read_text())["@context"]})
        with self.assertRaisesRegex(ValueError, "canonical FHP"):
            make_jsonld.fhp_canonical_record(document)

    def test_unsupported_jsonld_version_is_rejected(self):
        for version in (1.0, 2.0, "1.1"):
            with self.subTest(version=version):
                context = {**self.document["@context"], "@version": version}
                document = {**self.document, "@context": context}
                with self.assertRaisesRegex(ValueError, "@version"):
                    make_jsonld.fhp_canonical_record(document)

    def test_known_context_url_is_served_offline(self):
        for url in make_jsonld.FHP_KNOWN_CONTEXT_URLS:
            with self.subTest(url=url):
                document = dict(self.document, **{"@context": url})
                self.assertTrue(make_jsonld.fhp_is_canonical(document))
                self.assertTrue(equal(make_jsonld.fhp_canonical_record(document), self.record))

    def test_loader_never_fetches(self):
        for url in ("https://schema.org/", "https://example.org/fhp.jsonld", ""):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "nothing is fetched"):
                    make_jsonld.fhp_load_context(url)

    def test_root_id_is_set_aside(self):
        document = dict(self.document, **{"@id": "https://example.org/proteome"})
        warnings = []
        back = make_jsonld.fhp_canonical_record(document, warn=warnings.append)
        self.assertTrue(equal(back, self.record))
        self.assertEqual(len(warnings), 1)

    def test_export_document_is_not_fhp_metadata(self):
        export = json.loads(
            (ROOT / "examples" / "example.fhr.export.jsonld").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "FHP"):
            make_jsonld.fhp_canonical_record(export)


def fhp_loader(url, options=None):
    """Bundled-only FHP document loader: known context URLs, nothing else."""
    if url in make_jsonld.FHP_KNOWN_CONTEXT_URLS:
        return {"contextUrl": None, "documentUrl": url,
                "document": make_jsonld.load_fhp_context()}
    raise pyld.JsonLdError(f"not available offline: {url}", "jsonld.LoadDocumentError",
                           code="loading document failed")


@unittest.skipIf(pyld is None, "PyLD is not installed: pip install -r requirements-jsonld.txt")
class ProcessorTests(unittest.TestCase):
    """PyLD 3.3.0 expansion and compaction with a bundled-only loader."""

    @classmethod
    def setUpClass(cls):
        cls.examples = examples()
        cls.context = make_jsonld.load_fhp_context()

    def test_expand_and_compact_back(self):
        for name, record in self.examples.items():
            with self.subTest(record=name):
                document = make_jsonld.fhp_to_jsonld(record)
                expanded = pyld.expand(document, {"documentLoader": fhp_loader})
                compacted = pyld.compact(expanded, self.context, {"documentLoader": fhp_loader})
                back = make_jsonld.fhp_canonical_record(compacted, warn=lambda message: None)
                self.assertTrue(equal(back, record), json.dumps(back, indent=1))

    def test_known_context_url_expands_like_the_embedded_context(self):
        record = self.examples["minimal-database"]
        embedded = make_jsonld.fhp_to_jsonld(record)
        by_url = dict(embedded, **{"@context": make_jsonld.FHP_RAW_MAIN_CONTEXT_URL})
        self.assertEqual(pyld.expand(embedded, {"documentLoader": fhp_loader}),
                         pyld.expand(by_url, {"documentLoader": fhp_loader}))

    def test_loader_refuses_other_urls(self):
        document = dict(make_jsonld.fhp_to_jsonld(self.examples["minimal-predicted"]),
                        **{"@context": "https://schema.org/"})
        with self.assertRaises(pyld.JsonLdError):
            pyld.expand(document, {"documentLoader": fhp_loader})

    def test_expanded_predicates_are_schema_org_or_fhr(self):
        document = make_jsonld.fhp_to_jsonld(self.examples["rich-predicted"])
        expanded = pyld.expand(document, {"documentLoader": fhp_loader})
        predicates = set()

        def walk(node):
            if isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, dict):
                if "@value" in node:
                    return
                if "@list" in node:
                    walk(node["@list"])
                    return
                for key, value in node.items():
                    if not key.startswith("@"):
                        predicates.add(key)
                        walk(value)

        walk(expanded)
        self.assertTrue(predicates)
        for predicate in predicates:
            self.assertTrue(predicate.startswith((SDO, FHR)), predicate)


class DocumentationTests(unittest.TestCase):
    def test_draft_status_is_documented(self):
        fhp = (ROOT / "docs" / "FHP.md").read_text(encoding="utf-8")
        jsonld = (ROOT / "docs" / "JSONLD.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for text, name in ((fhp, "docs/FHP.md"), (jsonld, "docs/JSONLD.md"),
                           (changelog, "CHANGELOG.md")):
            with self.subTest(document=name):
                self.assertIn("FAIR-bioHeaders-Tools#58", text)
        self.assertIn("fhp.context.jsonld", fhp)
        self.assertIn("draft", fhp.lower())
        # Canonical JSON-LD is loss-preserving; schema.org export is one-way.
        self.assertIn("one-way", fhp.lower())


if __name__ == "__main__":
    unittest.main()
