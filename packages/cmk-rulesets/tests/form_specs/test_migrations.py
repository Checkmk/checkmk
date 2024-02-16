# !/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import nullcontext as does_not_raise
from typing import ContextManager, NamedTuple, TypeVar

import pytest

from cmk.rulesets.v1.form_specs import (
    LevelsConfigModel,
    migrate_to_lower_float_levels,
    migrate_to_lower_integer_levels,
    migrate_to_upper_float_levels,
    migrate_to_upper_integer_levels,
)

_NumberT = TypeVar("_NumberT", float, int)


def _to_levels_test_cases(ntype: type[_NumberT]) -> list[NamedTuple]:
    return [
        pytest.param(
            None,
            does_not_raise(),
            ("no_levels", None),
            id="None",
        ),
        pytest.param(
            (None, None),
            does_not_raise(),
            ("no_levels", None),
            id="(None, None)",
        ),
        pytest.param(
            ("no_levels", None),
            does_not_raise(),
            ("no_levels", None),
            id="already migrated no_levels",
        ),
        pytest.param(
            ("fixed", (ntype(50), ntype(60))),
            does_not_raise(),
            ("fixed", (ntype(50), ntype(60))),
            id="already migrated fixed_levels",
        ),
        pytest.param(
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            id="already migrated absolute predictive_levels",
        ),
        pytest.param(
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("relative", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("relative", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            id="already migrated relative predictive_levels",
        ),
        pytest.param(
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("stdev", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("stdev", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            id="already migrated stdev predictive_levels",
        ),
        pytest.param(
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (10, 15),
                },
            ),
            pytest.raises(TypeError),
            None,
            id="invalid migrated predictive_levels",
        ),
        pytest.param(
            (ntype(50), ntype(60)),
            does_not_raise(),
            ("fixed", (ntype(50), ntype(60))),
            id="migrate fixed levels/SimpleLevels",
        ),
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
            },
            does_not_raise(),
            ("no_levels", None),
            id="migrate predictive levels missing key for level direction",
        ),
        pytest.param(
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absotypolute", (ntype(10), ntype(20))),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            pytest.raises(TypeError),
            None,
            id="wrong predictive Levels",
        ),
        pytest.param(
            50.0,
            pytest.raises(TypeError),
            None,
            id="wrong_type",
        ),
        pytest.param(
            (50.0, 60.0, 70.0),
            pytest.raises(TypeError),
            None,
            id="wrong_length",
        ),
    ]


def _to_lower_levels_test_cases(ntype: type[_NumberT]) -> list[NamedTuple]:
    return _to_levels_test_cases(ntype) + [
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
                "levels_lower": ("absolute", (ntype(10), ntype(20))),
                "levels_upper_min": (ntype(10), ntype(15)),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "period": "wday",
                    "bound": None,
                },
            ),
            id="migrate absolute predictive levels lower",
        ),
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
                "levels_lower": ("relative", (10.0, 20.0)),
                "levels_upper_min": (ntype(10), ntype(15)),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("relative", (10.0, 20.0)),
                    "period": "wday",
                    "bound": None,
                },
            ),
            id="migrate relative predictive levels lower",
        ),
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
                "levels_lower": ("stdev", (10.0, 20.0)),
                "levels_upper_min": (ntype(10), ntype(15)),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("stdev", (10.0, 20.0)),
                    "period": "wday",
                    "bound": None,
                },
            ),
            id="migrate stdev predictive levels lower",
        ),
    ]


def _to_upper_levels_test_cases(ntype: type[_NumberT]) -> list[NamedTuple]:
    return _to_levels_test_cases(ntype) + [
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
                "levels_upper": ("absolute", (ntype(10), ntype(20))),
                "levels_upper_min": (ntype(10), ntype(15)),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            id="migrate absolute predictive levels upper",
        ),
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
                "levels_upper": ("relative", (10.0, 20.0)),
                "levels_upper_min": (ntype(10), ntype(15)),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("relative", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            id="migrate relative predictive levels upper",
        ),
        pytest.param(
            {
                "__injected__": None,
                "period": "wday",
                "horizon": 90,
                "levels_upper": ("stdev", (10.0, 20.0)),
                "levels_upper_min": (ntype(10), ntype(15)),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("stdev", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            id="migrate stdev predictive levels upper",
        ),
    ]


@pytest.mark.parametrize(
    ["input_value", "expected_raises", "expected_value"],
    _to_upper_levels_test_cases(float)
    + [
        pytest.param(
            {
                "horizon": 90,
                "levels_upper": ("absolute", (10, 20)),
                "period": "wday",
                "levels_upper_min": (10, 15),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (10.0, 15.0),
                },
            ),
            id="int to float",
        ),
    ],
)
def test_migrate_to_upper_float_levels(
    input_value: object,
    expected_raises: ContextManager[pytest.ExceptionInfo[TypeError]],
    expected_value: LevelsConfigModel[float],
) -> None:
    with expected_raises:
        assert expected_value == migrate_to_upper_float_levels(input_value)


@pytest.mark.parametrize(
    ["input_value", "expected_raises", "expected_value"],
    _to_lower_levels_test_cases(float)
    + [
        pytest.param(
            {
                "horizon": 90,
                "levels_lower": ("absolute", (10, 20)),
                "period": "wday",
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (10.0, 20.0)),
                    "period": "wday",
                    "bound": None,
                },
            ),
            id="int to float",
        ),
    ],
)
def test_migrate_to_lower_float_levels(
    input_value: object,
    expected_raises: ContextManager[pytest.ExceptionInfo[TypeError]],
    expected_value: LevelsConfigModel[float],
) -> None:
    with expected_raises:
        assert expected_value == migrate_to_lower_float_levels(input_value)


@pytest.mark.parametrize(
    ["input_value", "expected_raises", "expected_value"],
    _to_lower_levels_test_cases(int)
    + [
        pytest.param(
            {
                "horizon": 90,
                "levels_lower": ("absolute", (10.0, 20.0)),
                "period": "wday",
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (10, 20)),
                    "period": "wday",
                    "bound": None,
                },
            ),
            id="float to int",
        ),
    ],
)
def test_migrate_to_lower_integer_levels(
    input_value: object,
    expected_raises: ContextManager[pytest.ExceptionInfo[TypeError]],
    expected_value: LevelsConfigModel[int],
) -> None:
    with expected_raises:
        assert expected_value == migrate_to_lower_integer_levels(input_value)


@pytest.mark.parametrize(
    ["input_value", "expected_raises", "expected_value"],
    _to_upper_levels_test_cases(int)
    + [
        pytest.param(
            {
                "horizon": 90,
                "levels_upper": ("absolute", (10.0, 20.0)),
                "period": "wday",
                "levels_upper_min": (10.0, 15.0),
            },
            does_not_raise(),
            (
                "predictive",
                {
                    "horizon": 90,
                    "levels": ("absolute", (10, 20)),
                    "period": "wday",
                    "bound": (10, 15),
                },
            ),
            id="float to int",
        ),
    ],
)
def test_migrate_to_upper_int_levels(
    input_value: object,
    expected_raises: ContextManager[pytest.ExceptionInfo[TypeError]],
    expected_value: LevelsConfigModel[int],
) -> None:
    with expected_raises:
        assert expected_value == migrate_to_upper_integer_levels(input_value)
