#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for EC query filter operators."""

import pytest

from cmk.ec.query import MKClientError, operator_for


def test_tilde_tilde_lowercase_pattern_matches_mixed_case_value() -> None:
    _, cmp = operator_for("~~")
    assert cmp("Hello World", "hello") is True


def test_tilde_tilde_lowercase_pattern_matches_uppercase_value() -> None:
    _, cmp = operator_for("~~")
    assert cmp("HELLO WORLD", "hello") is True


def test_tilde_tilde_uppercase_pattern_matches_lowercase_value() -> None:
    _, cmp = operator_for("~~")
    assert cmp("hello world", "HELLO") is True


def test_tilde_tilde_regex_with_mixed_case_components() -> None:
    _, cmp = operator_for("~~")
    assert cmp("FooBar", "foo.*bar") is True


def test_tilde_tilde_no_match() -> None:
    _, cmp = operator_for("~~")
    assert cmp("hello", "xyz") is False


def test_tilde_tilde_anchored_pattern_matches_lowercase_start() -> None:
    _, cmp = operator_for("~~")
    assert cmp("Hello", "^he") is True


def test_tilde_tilde_differs_from_case_sensitive_tilde() -> None:
    _, case_sensitive = operator_for("~")
    _, case_insensitive = operator_for("~~")

    assert case_sensitive("Hello", "hello") is False
    assert case_insensitive("Hello", "hello") is True


def test_tilde_tilde_keeps_the_meaning_of_uppercase_regex_escapes() -> None:
    _, cmp = operator_for("~~")
    assert cmp("Disk full", r"^\S+ full$") is True


def test_eq_tilde_differs_only_in_case() -> None:
    _, cmp = operator_for("=~")
    assert cmp("Hello", "hello") is True


def test_eq_tilde_all_uppercase_equals_all_lowercase() -> None:
    _, cmp = operator_for("=~")
    assert cmp("HELLO", "hello") is True


def test_eq_tilde_different_strings_do_not_match() -> None:
    _, cmp = operator_for("=~")
    assert cmp("hello", "world") is False


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
    _, cmp = operator_for(operator_name)
    assert cmp(value, argument) is expected


def test_unknown_operator_raises() -> None:
    with pytest.raises(MKClientError, match="Unknown filter operator"):
        operator_for("??")
