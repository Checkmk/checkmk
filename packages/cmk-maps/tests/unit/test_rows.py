#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon typed Livestatus-row accessors (cmk.maps.shared.rows)."""

import pytest

from cmk.maps.shared.rows import (
    row_bool,
    row_dict,
    row_float,
    row_float_or_none,
    row_int,
    row_list,
    row_str,
    row_strs,
)


def test_row_str_returns_string() -> None:
    assert row_str(["a", "b"], 1) == "b"


def test_row_str_out_of_range_returns_default() -> None:
    assert row_str(["a"], 5, "x") == "x"


def test_row_str_non_string_returns_default() -> None:
    # A numeric cell read through the string accessor yields the default, not a
    # stringified number — the accessor is type-aware, not a str() coercion.
    assert row_str([5], 0) == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(5, 5, id="int"),
        pytest.param(5.9, 5, id="float-truncates"),
        pytest.param(-3, -3, id="negative-int"),
        pytest.param(True, 1, id="bool-true"),
        pytest.param(False, 0, id="bool-false"),
        pytest.param("7", 7, id="numeric-string"),
    ],
)
def test_row_int_coercions(value: object, expected: int) -> None:
    assert row_int([value], 0) == expected


def test_row_int_unparseable_string_returns_default() -> None:
    assert row_int(["nope"], 0, default=3) == 3


def test_row_int_out_of_range_returns_default() -> None:
    assert row_int([], 0, default=9) == 9


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(5, 5.0, id="int"),
        pytest.param(5.5, 5.5, id="float"),
        pytest.param(True, 1.0, id="bool"),
        pytest.param("2.5", 2.5, id="numeric-string"),
    ],
)
def test_row_float_coercions(value: object, expected: float) -> None:
    assert row_float([value], 0) == expected


def test_row_float_unparseable_string_returns_default() -> None:
    assert row_float(["nope"], 0, default=1.5) == 1.5


def test_row_bool_truthy_int() -> None:
    assert row_bool([1], 0) is True


def test_row_bool_zero_is_false() -> None:
    assert row_bool([0], 0) is False


def test_row_bool_out_of_range_uses_default() -> None:
    assert row_bool([], 0, default=True) is True
    assert row_bool([], 0, default=False) is False


def test_row_float_or_none_positive_value() -> None:
    assert row_float_or_none([3.5], 0) == 3.5


def test_row_float_or_none_zero_sentinel_is_none() -> None:
    assert row_float_or_none([0], 0) is None


def test_row_float_or_none_negative_is_none() -> None:
    # The >0 sentinel treats non-positive (never-checked, missing) as None.
    assert row_float_or_none([-1.0], 0) is None


def test_row_float_or_none_out_of_range_is_none() -> None:
    assert row_float_or_none([], 0) is None


def test_row_list_value() -> None:
    assert row_list([["a", "b"]], 0) == ["a", "b"]


def test_row_list_non_list_is_empty() -> None:
    assert row_list(["x"], 0) == []


def test_row_strs_filters_falsy_and_stringifies() -> None:
    assert row_strs([[1, "", "b", 0]], 0) == ["1", "b"]


def test_row_dict_value() -> None:
    assert row_dict([{"k": "v"}], 0) == {"k": "v"}


def test_row_dict_non_dict_is_empty() -> None:
    assert row_dict(["x"], 0) == {}
