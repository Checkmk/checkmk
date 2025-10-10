#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Any

import pytest

from cmk.ccc.crash_reporting import format_var_for_export, REDACTED_STRING


def test_format_var_for_export_strip_large_data() -> None:
    orig_var = {
        "a": {"y": ("a" * 1024 * 1024) + "a"},
    }

    var = copy.deepcopy(orig_var)
    formated: Any = format_var_for_export(var)

    # Stripped?
    assert formated["a"]["y"].endswith("(1 bytes stripped)")

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_nested_dict_with_list() -> None:
    orig_var: dict[str, object] = {
        "a": {
            "b": {
                "c": [{}],
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated: Any = format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"][0] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_nested_dict() -> None:
    orig_var: dict[str, object] = {
        "a": {
            "b": {
                "c": {
                    "d": {},
                },
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated: Any = format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"]["d"] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


NOT_MODIFIED = object()


@pytest.mark.parametrize(
    "input_,output",
    (
        ("foo", NOT_MODIFIED),
        ({"secret": "secret"}, {"secret": REDACTED_STRING}),
        ({("secret", 1): "secret"}, NOT_MODIFIED),
        (
            ["secret", 1],
            NOT_MODIFIED,
        ),
        (
            ["secret", 1, {"secret": "secret"}],
            ["secret", 1, {"secret": REDACTED_STRING}],
        ),
    ),
)
def test_format_var_for_export(input_: object, output: object) -> None:
    if output is NOT_MODIFIED:
        output = input_

    assert format_var_for_export(input_) == output
