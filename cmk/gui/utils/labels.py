#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from six import ensure_str
from typing import (
    Iterable,
    Mapping,
    Tuple,
)
from livestatus import (
    lqencode,
    quote_dict,
)
from cmk.gui.i18n import _

Labels = Iterable[Tuple[str, str]]


def encode_label_for_livestatus(
    column: str,
    label_id: str,
    label_value: str,
) -> str:
    """
    >>> encode_label_for_livestatus("labels", "key", "value")
    "Filter: labels = 'key' 'value'"
    """
    return "Filter: %s = %s %s" % (
        lqencode(column),
        lqencode(quote_dict(label_id)),
        lqencode(quote_dict(label_value)),
    )


def encode_labels_for_livestatus(
    column: str,
    labels: Labels,
) -> str:
    """
    >>> encode_labels_for_livestatus("labels", {"key": "value", "x": "y"}.items())
    "Filter: labels = 'key' 'value'\\nFilter: labels = 'x' 'y'"
    >>> encode_labels_for_livestatus("labels", [])
    ''
    """
    return "\n".join(
        encode_label_for_livestatus(column, label_id, label_value)
        for label_id, label_value in labels)


def encode_labels_for_tagify(labels: Labels) -> Iterable[Mapping[str, str]]:
    """
    >>> encode_labels_for_tagify({"key": "value", "x": "y"}.items())
    [{'value': 'key:value'}, {'value': 'x:y'}]
    """
    return [{"value": "%s:%s" % e} for e in labels]


def encode_labels_for_http(labels: Labels) -> str:
    """The result can be used in building URLs
    >>> encode_labels_for_http([])
    ''
    >>> encode_labels_for_http({"key": "value", "x": "y"}.items())
    '[{"value": "key:value"}, {"value": "x:y"}]'
    """
    # tagify outputs a warning for value of "[]" right now
    # see: https://github.com/yairEO/tagify/pull/275
    encoded_labels = encode_labels_for_tagify(labels)
    return ensure_str(json.dumps(encoded_labels)) if encoded_labels else ""


def label_help_text() -> str:
    return _(
        "Labels need to be in the format <tt>[KEY]:[VALUE]</tt>. For example <tt>os:windows</tt>.")
