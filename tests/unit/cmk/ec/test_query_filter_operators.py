#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for EC query filter operators."""

import pytest

from cmk.ec.query import operator_for


def test_tilde_tilde_keeps_the_meaning_of_uppercase_regex_escapes() -> None:
    _, func = operator_for("~~")
    assert func("Disk full", r"^\S+ full$") is True


# fmt: off
@pytest.mark.parametrize(
    "operator_name, value, argument, expected",
    [
        pytest.param("!=",  "Hello", "Hello", False, id="not equal, same value"),
        pytest.param("!=",  "Hello", "hello", True,  id="not equal, value differs in case"),
        pytest.param("!=~", "Hello", "hello", False, id="not equal ignoring case, value differs in case"),
        pytest.param("!=~", "Hello", "world", True,  id="not equal ignoring case, different value"),
        pytest.param("!~",  "Hello", "^He",   False, id="regex does not match, matching value"),
        pytest.param("!~",  "Hello", "^he",   True,  id="regex does not match, value differs in case"),
        pytest.param("!~~", "Hello", "^he",   False, id="regex does not match ignoring case, value differs in case"),
        pytest.param("!~~", "Hello", "^wo",   True,  id="regex does not match ignoring case, non-matching value"),
    ],
)
# fmt: on
def test_negated_operator_holds_only_if_the_value_does_not_match(
    operator_name: str, value: str, argument: str, expected: bool
) -> None:
    _, func = operator_for(operator_name)
    assert func(value, argument) is expected
