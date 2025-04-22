#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Collection, Mapping
from numbers import Number
from typing import Any, Final
from xml.dom.minidom import Document, parseString
from xml.parsers.expat import ExpatError

_ROOT_TAG_NAME: Final = "root"
_LIST_ITEM_NAME: Final = "item"
_FALLBACK_TAG_NAME: Final = "key"


def dict_to_document(data: Mapping[str, Any]) -> Document:
    return parseString(_render(_ROOT_TAG_NAME, data))


def _render(tag: str, value: Any, attrs: str = "") -> str:
    if isinstance(value, Mapping):
        rendered = "".join(_render(*_preprocess(k, v)) for k, v in value.items())
        return f"<{tag} {attrs}>{rendered}</{tag}>"

    if not isinstance(value, str) and isinstance(value, Collection):
        rendered = "".join(_render(*_preprocess(_LIST_ITEM_NAME, v)) for v in value)
        return f"<{tag} {attrs}>{rendered}</{tag}>"

    return _render_atomic_value(tag, value, attrs)


def _render_atomic_value(tag: str, value: Any, attrs: str) -> str:
    match value:
        case str(val):
            return f"<{tag}{attrs}>{_escape_xml(val)}</{tag}>"
        case bool(val):
            return f"<{tag}{attrs}>{str(val).lower()}</{tag}>"
        case val if isinstance(val, datetime.datetime | datetime.date):
            return f"<{tag}{attrs}>{val.isoformat()}</{tag}>"
        case None:
            return f"<{tag}{attrs}></{tag}>"
        case _:
            return f"<{tag}{attrs}>{value}</{tag}>"


def _preprocess(tag: str, value: Any) -> tuple[str, Any, str]:
    tag_ = _escape_xml(tag).replace(" ", "_")
    xml_type = _get_xml_type(value)

    if not _is_valid_tag(tag_):
        return _FALLBACK_TAG_NAME, value, f' name="{tag_}" type="{xml_type}"'

    return tag_, value, f' type="{xml_type}"'


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _get_xml_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str | datetime.datetime | datetime.date):
        return "str"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, Number):
        return "number"
    if isinstance(value, Mapping):
        return "dict"
    if isinstance(value, Collection):
        return "list"
    raise TypeError(f"Invalid XML type: {value} ({type(value).__name__})")


def _is_valid_tag(tag: str) -> bool:
    try:
        parseString(f"<{tag}></{tag}>")
    except ExpatError:
        return False

    return True
