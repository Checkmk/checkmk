#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal helper for rendering HTML tags"""

import re
from typing import cast, Dict, Iterator, List, Optional, Union

from cmk.gui.type_defs import CSSSpec
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML

HTMLTagName = str
HTMLTagValue = Optional[str]
HTMLContent = Union[None, int, HTML, str]
HTMLTagAttributeValue = Union[None, CSSSpec, HTMLTagValue, List[str]]
HTMLTagAttributes = Dict[str, HTMLTagAttributeValue]

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


def render_start_tag(
    tag_name: HTMLTagName, close_tag: bool = False, **attrs: HTMLTagAttributeValue
) -> HTML:
    """You have to replace attributes which are also python elements such as
    'class', 'id', 'for' or 'type' using a trailing underscore (e.g. 'class_' or 'id_')."""
    return HTML(
        "<%s%s%s>"
        % (
            tag_name,
            "" if not attrs else "".join(_render_attributes(**attrs)),
            "" if not close_tag else " /",
        )
    )


def render_end_tag(tag_name: HTMLTagName) -> HTML:
    return HTML("</%s>" % (tag_name))


def render_element(
    tag_name: HTMLTagName, tag_content: HTMLContent, **attrs: HTMLTagAttributeValue
) -> HTML:
    open_tag = render_start_tag(tag_name, close_tag=False, **attrs)

    if not tag_content:
        tag_content = ""
    elif not isinstance(tag_content, HTML):
        tag_content = escaping.escape_text(tag_content)

    return HTML("%s%s</%s>" % (open_tag, tag_content, tag_name))


def _render_attributes(**attrs: HTMLTagAttributeValue) -> Iterator[str]:
    css = _get_normalized_css_classes(attrs)
    if css:
        attrs["class"] = css

    # options such as 'selected' and 'checked' dont have a value in html tags
    options = []

    # Links require href to be first attribute
    href = attrs.pop("href", None)
    if href:
        attributes = list(attrs.items())
        attributes.insert(0, ("href", href))
    else:
        attributes = list(attrs.items())

    # render all attributes
    for key_unescaped, v in attributes:
        if v is None:
            continue

        key = escaping.escape_attribute(key_unescaped.rstrip("_"))

        if key.startswith("data_"):
            key = key.replace("_", "-", 1)  # HTML data attribute: 'data-name'

        if v == "":
            options.append(key)
            continue

        if not isinstance(v, list):
            v = escaping.escape_attribute(v)
        else:
            if key == "class":
                sep = " "
            elif key == "style" or key.startswith("on"):
                sep = "; "
            else:
                # TODO: Can we drop this special Feature? No idea what it is used for.
                sep = "_"

            joined_value = sep.join([a for a in (escaping.escape_attribute(vi) for vi in v) if a])

            # TODO: Can we drop this special feature? Find an cleanup the call sites
            if sep.startswith(";"):
                joined_value = re.sub(";+", ";", joined_value)

            v = joined_value

        yield ' %s="%s"' % (key, v)

    for k in options:
        yield " %s=''" % k


def normalize_css_spec(css_classes: CSSSpec) -> List[str]:
    if isinstance(css_classes, list):
        return [c for c in css_classes if c is not None]

    if css_classes is not None:
        return [css_classes]

    return []


def _get_normalized_css_classes(attrs: HTMLTagAttributes) -> List[str]:
    # make class attribute foolproof
    css: List[str] = []
    for k in ["class_", "css", "cssclass", "class"]:
        if k in attrs:
            cls_spec = cast(CSSSpec, attrs.pop(k))
            css += normalize_css_spec(cls_spec)
    return css
