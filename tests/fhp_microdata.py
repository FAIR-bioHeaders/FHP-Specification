# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Test-only FHP HTML microdata reader and writer.

Implements the draft binding in ``docs/FHP-MICRODATA.md`` on top of the shared
rules M1 to M4 and R9 in ``docs/MICRODATA.md``. It is deliberately small and
standard-library only (``html.parser``). It is **not** a runtime parser: the
reader and writer shipped to users stay in the toolkit
(FAIR-bioHeaders-Tools#58). Tests use it to prove that the committed examples
round-trip to their canonical records and that the negative fixtures are
rejected.

The writer emits the converter's typed serialization (``data-fhr-type``
annotations, array containers with ``itemprop="item"`` children) so a typed
record can be recovered exactly. The reader also accepts the untyped fallback:
without ``data-fhr-type`` it converts values using the selected JSON Schema's
types, as rule M3 requires.
"""

import json
import re
from html import escape
from html.parser import HTMLParser

# The raw-main FHP schema URL is the record's itemtype identity
# (docs/SCHEMA-VERSIONS.md; docs/MICRODATA.md M1). The pre-rename repository
# name is the same file and the same item type.
FHP_ITEMTYPE = (
    "https://raw.githubusercontent.com/FAIR-bioHeaders/"
    "FAIR-bioHeaders-Specification/main/fhp.json"
)
FHP_ITEMTYPE_OLD_NAME = (
    "https://raw.githubusercontent.com/FAIR-bioHeaders/"
    "FHR-Specification/main/fhp.json"
)
FHP_ITEMTYPES = {FHP_ITEMTYPE, FHP_ITEMTYPE_OLD_NAME}

# The `schema` itemprop selects the contract version. It is an FHP schema URL:
# a raw GitHub URL naming `main` or a release tag, or a w3id release URL
# (docs/SCHEMA-VERSIONS.md V1 to V4). Any other ref is unsupported-version.
FHP_SCHEMA_URL = re.compile(
    r"^https://raw\.githubusercontent\.com/FAIR-bioHeaders/"
    r"(FHR|FAIR-bioHeaders)-Specification/(main|v[0-9]+\.[0-9]+\.[0-9]+)/fhp\.json$"
)
FHP_W3ID_URL = re.compile(
    r"^https://w3id\.org/fair-bioheaders/fhp/v[0-9]+\.[0-9]+\.[0-9]+/?$"
)

# Elements whose end tag HTML implies (docs/MICRODATA.md M2).
_VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}
_AUTO_CLOSE = {
    "li": {"li"},
    "dt": {"dt", "dd"},
    "dd": {"dt", "dd"},
    "tr": {"tr"},
    "td": {"td", "th"},
    "th": {"td", "th"},
    "p": {"p"},
}
# Elements whose defining attribute is the property value (docs/MICRODATA.md M2).
_VALUE_ATTRIBUTE = {
    "meta": "content",
    "a": "href", "area": "href", "link": "href",
    "audio": "src", "embed": "src", "iframe": "src", "img": "src",
    "source": "src", "track": "src", "video": "src",
    "object": "data",
    "data": "value", "meter": "value",
    "time": "datetime",
}
_TYPED = {"string", "integer", "number", "boolean", "null"}


class MicrodataError(ValueError):
    """The document is not valid FHP microdata."""


class _Node:
    __slots__ = ("tag", "attrs", "children", "itemscope", "itemtype", "itemprop",
                 "datatype")

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.itemscope = "itemscope" in attrs
        self.itemtype = attrs.get("itemtype", "").split()
        self.itemprop = attrs.get("itemprop", "").split()
        self.datatype = attrs.get("data-fhr-type")


def _first_wins(attrs):
    """R9: the first of repeated attributes applies."""
    result = {}
    for name, value in attrs:
        if name not in result:
            result[name] = "" if value is None else value
    return result


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        while len(self.stack) > 1 and self.stack[-1].tag in _AUTO_CLOSE.get(tag, ()):
            self.stack.pop()
        node = _Node(tag, _first_wins(attrs))
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, _first_wins(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _nodes(node):
    for child in node.children:
        if isinstance(child, _Node):
            yield child
            yield from _nodes(child)


def _text(node):
    parts = []
    for child in node.children:
        parts.append(child if isinstance(child, str) else _text(child))
    return "".join(parts)


def _value_of(element):
    attribute = _VALUE_ATTRIBUTE.get(element.tag)
    if attribute and attribute in element.attrs:
        return element.attrs[attribute]
    return _text(element)


def _resolve(root, subschema):
    while isinstance(subschema, dict) and "$ref" in subschema:
        reference = subschema["$ref"]
        if not reference.startswith("#/$defs/"):
            raise MicrodataError(f"unsupported $ref {reference!r}")
        subschema = root["$defs"][reference.rsplit("/", 1)[-1]]
    return subschema


def _json_type(root, subschema):
    resolved = _resolve(root, subschema)
    if "type" in resolved:
        return resolved["type"]
    branches = resolved.get("anyOf") or resolved.get("oneOf")
    if branches:
        types = {_json_type(root, branch) for branch in branches}
        if len(types) == 1:
            return types.pop()
    return None


def _subschema(root, parent, name):
    return _resolve(root, parent).get("properties", {}).get(name, {})


def _parse_typed(raw, datatype):
    if datatype == "string":
        return raw
    try:
        value = json.loads(raw)
    except ValueError as error:
        raise MicrodataError(f"{datatype} value is not JSON: {raw!r}") from error
    if datatype == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise MicrodataError(f"integer value is not an integer: {raw!r}")
    elif datatype == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MicrodataError(f"number value is not a number: {raw!r}")
    elif datatype == "boolean":
        if not isinstance(value, bool):
            raise MicrodataError(f"boolean value is not a boolean: {raw!r}")
    elif datatype == "null":
        if value is not None:
            raise MicrodataError(f"null value is not null: {raw!r}")
    else:
        raise MicrodataError(f"unknown data-fhr-type {datatype!r}")
    return value


def _convert_untyped(raw, root, subschema):
    kind = _json_type(root, subschema)
    if kind in ("integer", "number", "boolean"):
        return _parse_typed(raw, kind)
    return raw


def _property_elements(scope):
    """Yield (element, property name) for the item's own properties (M1)."""
    def walk(node):
        for child in node.children:
            if not isinstance(child, _Node):
                continue
            if child.itemprop:
                for name in child.itemprop:
                    yield child, name
            elif child.itemscope:
                continue  # A separate item; its properties are not the parent's.
            else:
                yield from walk(child)
    yield from walk(scope)


def _read_value(element, root, subschema):
    datatype = element.datatype
    if datatype == "array":
        items = []
        for child in element.children:
            if isinstance(child, str):
                if child.strip():
                    raise MicrodataError("array container has stray text")
                continue
            if "item" not in child.itemprop:
                raise MicrodataError("array container child is not itemprop=item")
            items.append(_read_value(child, root,
                                     _resolve(root, subschema).get("items", {})))
        return items
    if datatype == "object":
        if not element.itemscope:
            raise MicrodataError("data-fhr-type=object without itemscope")
        return _read_scope(element, root, subschema)
    if datatype in _TYPED:
        return _parse_typed(_value_of(element), datatype)
    if datatype is not None:
        raise MicrodataError(f"unknown data-fhr-type {datatype!r}")
    if element.itemscope:
        return _read_scope(element, root, subschema)
    return _convert_untyped(_value_of(element), root, subschema)


def _read_scope(scope, root, subschema):
    occurrences = {}
    for element, name in _property_elements(scope):
        value = _read_value(element, root, _subschema(root, subschema, name))
        occurrences.setdefault(name, []).append(value)
    record = {}
    for name, values in occurrences.items():
        field = _subschema(root, subschema, name)
        if _json_type(root, field) == "array":
            flat = []
            for value in values:
                flat.extend(value if isinstance(value, list) else [value])
            record[name] = flat
        elif len(values) == 1:
            record[name] = values[0]
        else:
            record[name] = values  # M4: a repeated property becomes a list.
    return record


def read_page(text, schema):
    """Extract one FHP record from an HTML document.

    ``schema`` is the parsed FHP JSON Schema, used for the untyped fallback
    (M3). Raises :class:`MicrodataError` for a document that is not a single,
    structurally valid FHP item scope.
    """
    builder = _TreeBuilder()
    builder.feed(text)
    builder.close()
    scopes = [node for node in _nodes(builder.root) if node.itemscope]
    fhp_scopes = [node for node in scopes if FHP_ITEMTYPES & set(node.itemtype)]
    if len(fhp_scopes) != 1:
        raise MicrodataError(
            f"expected exactly one FHP item scope, found {len(fhp_scopes)}")
    record = _read_scope(fhp_scopes[0], schema, schema)
    selected = record.get("schema")
    if not isinstance(selected, str) or not (
            FHP_SCHEMA_URL.match(selected) or FHP_W3ID_URL.match(selected)):
        raise MicrodataError(f"unsupported FHP schema selection: {selected!r}")
    return record


def _write_property(name, value):
    prop = escape(name, quote=True)
    if isinstance(value, dict):
        content = "".join(_write_property(key, item) for key, item in value.items())
        return f'<span itemprop="{prop}" itemscope data-fhr-type="object">{content}</span>'
    if isinstance(value, list):
        content = "".join(_write_property("item", item) for item in value)
        return f'<span itemprop="{prop}" data-fhr-type="array">{content}</span>'
    if isinstance(value, bool):
        datatype, text = "boolean", json.dumps(value)
    elif isinstance(value, int):
        datatype, text = "integer", json.dumps(value)
    elif isinstance(value, float):
        datatype, text = "number", json.dumps(value)
    else:
        datatype, text = "string", value
    return f'<span itemprop="{prop}" data-fhr-type="{datatype}">{escape(text)}</span>'


def write_page(record, itemtype=FHP_ITEMTYPE, title="FHP microdata example"):
    """Write one record as a standalone HTML document (typed serialization)."""
    content = "".join(_write_property(name, value) for name, value in record.items())
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title></head><body>\n"
        f'<div itemscope itemtype="{escape(itemtype, quote=True)}">{content}</div>\n'
        "</body></html>\n"
    )
