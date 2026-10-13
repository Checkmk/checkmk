#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import override

import pytest

from cmk.gui.nagvis._php_formatter import format_php


class _EvulToStr:
    @override
    def __str__(self) -> str:
        return "' boom!"


# This is a regression test for CMK-11206.
@pytest.mark.parametrize(
    "python_data,expected",
    [
        # basic types
        (None, "null"),
        ("", "''"),
        ({}, "array(\n)"),
        (-5, "-5"),
        (3.14, "3.14"),
        (3e1, "30.0"),
        (
            {"a": "x", "b": False, "c": [1, "foo"]},
            "array(\n    'a' => 'x',\n    'b' => false,\n    'c' => array(\n        1,\n        'foo',\n    ),\n)",
        ),
        # escaping
        ("quote: '", r"'quote: \''"),
        ("backslash: \\", r"'backslash: \\'"),
        ("bsquote: \\'", r"'bsquote: \\\''"),
        # str() as fallback
        ({1, 2, 3}, "'{1, 2, 3}'"),
        (_EvulToStr(), r"'\' boom!'"),
    ],
)
def test_format_php(python_data: object, expected: str) -> None:
    assert format_php(python_data) == expected
