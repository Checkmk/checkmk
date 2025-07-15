#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal helper for rendering HTML tags"""

import re
from collections.abc import Iterator

from cmk.gui.type_defs import CSSSpec
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.utils import urls

HTMLTagName = str
HTMLTagValue = str | None
HTMLContent = int | HTML | str | None
HTMLTagAttributeValue = CSSSpec | HTMLTagValue | list[str] | None
HTMLTagAttributes = dict[str, HTMLTagAttributeValue]

__all__ = [
    "HTMLTagValue",
    "HTMLContent",
    "HTMLTagAttributeValue",
    "HTMLTagAttributes",
    "render_start_tag",
    "render_end_tag",
    "render_element",
    "normalize_css_spec",
]

_SUPPORTED_CSS_CLASS_KEYS = frozenset(["class_", "css", "cssclass", "class"])


def render_start_tag(
    tag_name: HTMLTagName, close_tag: bool = False, **attrs: HTMLTagAttributeValue
) -> HTML:
    """You have to replace attributes which are also python elements such as
    'class', 'id', 'for' or 'type' using a trailing underscore (e.g. 'class_' or 'id_')."""
    return HTML.without_escaping(
        "<%s%s%s>"
        % (
            tag_name,
            "" if not attrs else "".join(_render_attributes(**attrs)),
            "" if not close_tag else " /",
        )
    )


def render_end_tag(tag_name: HTMLTagName) -> HTML:
    return HTML.without_escaping("</%s>" % (tag_name))


def render_element(
    tag_name: HTMLTagName, tag_content: HTMLContent, **attrs: HTMLTagAttributeValue
) -> HTML:
    open_tag = render_start_tag(tag_name, close_tag=False, **attrs)

    if not tag_content:
        tag_content = ""
    elif not isinstance(tag_content, HTML):
        tag_content = escaping.escape_text(tag_content)

    return HTML.without_escaping(f"{open_tag}{tag_content}</{tag_name}>")


def _render_attributes(**attrs: HTMLTagAttributeValue) -> Iterator[str]:
    normalized = _attrs_with_normalized_class(attrs)
    yield from (f' {key}="{value}"' for key, value in _extract_attrs(normalized))
    yield from (f" {key}=''" for key in _extract_options(normalized))


def _extract_attrs(
    raw_attrs: dict[str, HTMLTagAttributeValue],
) -> Iterator[tuple[str, str]]:
    # Links require href to be first attribute
    attrs = {"href": href, **raw_attrs} if (href := raw_attrs.get("href", None)) else raw_attrs
    return (
        (_format_key(key), _format_value(key, val))
        for key, val in attrs.items()
        if val is not None and val != ""
    )


def _extract_options(raw_attrs: dict[str, HTMLTagAttributeValue]) -> Iterator[str]:
    # options such as 'selected' and 'checked' dont have a value in html tags
    return (_format_key(key) for key, val in raw_attrs.items() if val == "")


def _format_key(key: str) -> str:
    if (escaped_key := escaping.escape_attribute(key.rstrip("_"))).startswith("data_"):
        return escaped_key.replace("_", "-", 1)

    return escaped_key


def _format_value(key: str, value: str | list[str]) -> str:
    if isinstance(value, list):
        separator = _get_separator(key)
        joined = separator.join(escaping.escape_attribute(attr) for attr in value if attr)

        # TODO: Can we drop this special feature?
        if separator.startswith(";"):
            return re.sub(";+", ";", joined)

        return joined

    if key == "href" and urls.is_allowed_url(value):
        return value

    return escaping.escape_attribute(value)


def _get_separator(key: str) -> str:
    if key.startswith("on"):
        return "; "
    # TODO: Can we drop this special Feature? No idea what it is used for. (defaults to "_")
    return {"class": " ", "style": "; "}.get(key, "_")


def normalize_css_spec(css_classes: CSSSpec | str | None) -> list[str]:
    match css_classes:
        case [*css_specs]:
            return [c for c in css_specs if c is not None]
        case str(single_css_class):
            return [single_css_class]
        case _:
            return []


def _attrs_with_normalized_class(attrs: HTMLTagAttributes) -> HTMLTagAttributes:
    normalized = {}
    css = []

    for key, value in attrs.items():
        if key in _SUPPORTED_CSS_CLASS_KEYS:
            css += normalize_css_spec(value)
        else:
            normalized[key] = value

    if css:
        normalized["class"] = css

    return normalized
