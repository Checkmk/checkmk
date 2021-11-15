#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from deepdiff import DeepDiff  # type: ignore[import]
from deepdiff.helper import get_type  # type: ignore[import]

from cmk.utils.i18n import _

__all__ = [
    "make_object_diff",
]


def make_object_diff(old: Any, new: Any) -> str:
    """Creates a text representing the object differences for humans"""
    diff = DeepDiff(old, new, view="tree")
    text = pretty(diff)
    return text or _("Nothing was changed.")


def pretty(diff: DeepDiff) -> str:
    """Copy of DeepDiff.pretty() to execute our own pretty_print_diff()"""
    result = []
    keys = sorted(
        diff.tree.keys()
    )  # sorting keys to guarantee constant order across python versions.
    for key in keys:
        for item_key in diff.tree[key]:
            result += [pretty_print_diff(item_key)]

    return "\n".join(sorted(result))


PRETTY_FORM_TEXTS = {
    "type_changes": _("Value of {diff_path} changed from {val_t1} to {val_t2}."),
    "values_changed": _("Value of {diff_path} changed from {val_t1} to {val_t2}."),
    "dictionary_item_added": _("Attribute {diff_path} with value {val_t2} added."),
    "dictionary_item_removed": _("Attribute {diff_path} with value {val_t1} removed."),
    "iterable_item_added": _("Item {diff_path} with value {val_t2} added."),
    "iterable_item_removed": _("Item {diff_path} with value {val_t1} removed."),
    "attribute_added": _("Attribute {diff_path} with value {val_t2} added."),
    "attribute_removed": _("Attribute {diff_path} with value {val_t1} removed."),
    "set_item_added": _("Item {val_t2} added."),
    "set_item_removed": _("Item {val_t1} removed."),
    "repetition_change": _("Repetition change for item {diff_path}."),
}


def pretty_print_diff(diff: DeepDiff) -> str:
    """Copy of deepdiff.serialization.pretty_print_diff to slighlty adapt the output format"""
    type_t1 = get_type(diff.t1).__name__
    type_t2 = get_type(diff.t2).__name__

    val_t1 = '"{}"'.format(str(diff.t1)) if type_t1 == "str" else str(diff.t1)
    val_t2 = '"{}"'.format(str(diff.t2)) if type_t2 == "str" else str(diff.t2)

    return PRETTY_FORM_TEXTS.get(diff.report_type, "").format(
        diff_path=diff_path(diff), type_t1=type_t1, type_t2=type_t2, val_t1=val_t1, val_t2=val_t2
    )


def diff_path(diff: DeepDiff) -> str:
    """Reformat diff path to be a little more intuitive

    We could also build our own path renderer (See DiffLevel.path of deepdiff), but this seems to be
    good enough for the moment.
    """
    path = diff.path(root="")
    if path == "":
        return "object"  # The whole object changed it's value (e.g. "a" -> "b")

    return path.strip("[]").replace("['", "").replace("']", "/").replace("'", '"')
