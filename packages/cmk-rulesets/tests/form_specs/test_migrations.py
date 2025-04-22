#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext as does_not_raise
from typing import Literal, NamedTuple, TypeVar
from unittest.mock import ANY

import pytest

from cmk.rulesets.v1.form_specs import (
    LevelsConfigModel,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    migrate_to_lower_float_levels,
    migrate_to_lower_integer_levels,
    migrate_to_password,
    migrate_to_proxy,
    migrate_to_time_period,
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
                    "period": "minute",
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "bound": (ntype(10), ntype(15)),
                    "__reference_metric__": "pagefile_used",
                    "__direction__": "upper",
                },
            ),
            does_not_raise(),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "period": "minute",
                    "bound": (ntype(10), ntype(15)),
                    "__reference_metric__": "pagefile_used",
                    "__direction__": "upper",
                },
            ),
            id="2.3.0b3 format absolute predictive_levels",
        ),
        pytest.param(
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "horizon": 90,
                    "levels": ("absolute", (ntype(10), ntype(20))),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            does_not_raise(),
            (
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "horizon": 90,
                    "levels": ("relative", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            does_not_raise(),
            (
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "horizon": 90,
                    "levels": ("stdev", (10.0, 20.0)),
                    "period": "wday",
                    "bound": (ntype(10), ntype(15)),
                },
            ),
            does_not_raise(),
            (
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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
                "cmk_postprocessed",
                "predictive_levels",
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


def test_migrate_to_integer_simple_levels_scaled() -> None:
    old = (50, 60)
    scale = 0.1
    new = ("fixed", (5, 6))
    assert migrate_to_integer_simple_levels(old, scale) == new
    assert migrate_to_integer_simple_levels(new, scale) == new


def test_migrate_to_simple_float_levels_scaled() -> None:
    old = (50.0, 60.0)
    scale = 0.1
    new = ("fixed", (5.0, 6.0))
    assert migrate_to_float_simple_levels(old, scale) == new
    assert migrate_to_float_simple_levels(new, scale) == new


def test_migrate_to_upper_integer_levels_scaled() -> None:
    old = (50, 60)
    scale = 0.1
    new = ("fixed", (5, 6))
    assert migrate_to_lower_integer_levels(old, scale) == new
    assert migrate_to_lower_integer_levels(new, scale) == new


def test_migrate_to_upper_integer_levels_scaled_predictive_absolute() -> None:
    old = {"horizon": 90, "levels_upper": ("absolute", (1.0, 2.0)), "period": "wday"}
    scale = 1024**3
    new = (
        "cmk_postprocessed",
        "predictive_levels",
        {
            "horizon": 90,
            "period": "wday",
            "levels": ("absolute", (1024**3, 2 * 1024**3)),
            "bound": None,
        },
    )
    assert migrate_to_upper_integer_levels(old, scale) == new
    assert migrate_to_upper_integer_levels(new, scale) == new


def test_migrate_to_upper_integer_levels_scaled_predictive_relative() -> None:
    old = {
        "horizon": 90,
        "period": "wday",
        "levels_upper": ("relative", (10.0, 20.0)),
        "levels_upper_min": (1, 2),
    }
    scale = 1024**3
    new = (
        "cmk_postprocessed",
        "predictive_levels",
        {
            "horizon": 90,
            "levels": ("relative", (10.0, 20.0)),
            "period": "wday",
            "bound": (1024**3, 2 * 1024**3),
        },
    )
    assert migrate_to_upper_integer_levels(old, scale) == new
    assert migrate_to_upper_integer_levels(new, scale) == new


def test_migrate_to_upper_integer_levels_scaled_predictive_stdev() -> None:
    old = {
        "horizon": 90,
        "period": "wday",
        "levels_upper": ("stdev", (2.0, 4.0)),
        "levels_upper_min": (1, 2),
    }
    scale = 1024**3
    new = (
        "cmk_postprocessed",
        "predictive_levels",
        {
            "horizon": 90,
            "levels": ("stdev", (2.0, 4.0)),
            "period": "wday",
            "bound": (1024**3, 2 * 1024**3),
        },
    )
    assert migrate_to_upper_integer_levels(old, scale) == new
    assert migrate_to_upper_integer_levels(new, scale) == new


@pytest.mark.parametrize(
    ["old", "new"],
    [
        pytest.param(
            ("password", "secret-password"),
            (
                "cmk_postprocessed",
                "explicit_password",
                (ANY, "secret-password"),
            ),
            id="migrate explicit password",
        ),
        pytest.param(
            ("store", "password_1"),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="migrate stored password",
        ),
        pytest.param(
            ("explicit_password", "067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="old 3-tuple explicit password",
        ),
        pytest.param(
            ("stored_password", "password_1", ""),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="old 3-tuple stored password",
        ),
        pytest.param(
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="already migrated explicit password",
        ),
        pytest.param(
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="already migrated stored password",
        ),
    ],
)
def test_migrate_to_password(
    old: object,
    new: tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ],
) -> None:
    migrated_password = migrate_to_password(old)
    twice_migrated = migrate_to_password(migrated_password)
    assert migrated_password == new
    assert twice_migrated == new


def test_multiple_migrations_do_not_reuse_id() -> None:
    old = ("password", "secret-password")
    first_migration = migrate_to_password(old)
    second_migration = migrate_to_password(old)
    assert first_migration[2][0] != second_migration[2][0]


@pytest.mark.parametrize(
    ["old", "new"],
    [
        pytest.param(
            ("environment", "environment"),
            ("cmk_postprocessed", "environment_proxy", ""),
            id="migrate environment proxy",
        ),
        pytest.param(
            ("no_proxy", None),
            ("cmk_postprocessed", "no_proxy", ""),
            id="migrate no proxy",
        ),
        pytest.param(
            ("global", "global-proxy-id"),
            ("cmk_postprocessed", "stored_proxy", "global-proxy-id"),
            id="migrate stored proxy",
        ),
        pytest.param(
            ("url", "proxy_url"),
            ("cmk_postprocessed", "explicit_proxy", "proxy_url"),
            id="migrate explicit proxy",
        ),
        pytest.param(
            ("cmk_postprocessed", "environment_proxy", ""),
            ("cmk_postprocessed", "environment_proxy", ""),
            id="already migrated environment proxy",
        ),
        pytest.param(
            ("cmk_postprocessed", "no_proxy", ""),
            ("cmk_postprocessed", "no_proxy", ""),
            id="already migrated no proxy",
        ),
        pytest.param(
            ("cmk_postprocessed", "stored_proxy", "global-proxy-id"),
            ("cmk_postprocessed", "stored_proxy", "global-proxy-id"),
            id="already migrated stored proxy",
        ),
        pytest.param(
            ("cmk_postprocessed", "explicit_proxy", "proxy_url"),
            ("cmk_postprocessed", "explicit_proxy", "proxy_url"),
            id="already migrated explicit proxy",
        ),
    ],
)
def test_migrate_to_proxy(
    old: object,
    new: tuple[
        Literal["cmk_postprocessed"],
        Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
        str,
    ],
) -> None:
    assert migrate_to_proxy(old) == new
    assert migrate_to_proxy(new) == new


@pytest.mark.parametrize(
    ["old", "new"],
    [
        pytest.param(
            "24X7",
            ("cmk_postprocessed", "stored_time_period", "24X7"),
            id="migrate time period",
        ),
        pytest.param(
            ("cmk_postprocessed", "stored_time_period", "24X7"),
            ("cmk_postprocessed", "stored_time_period", "24X7"),
            id="already migrated time period",
        ),
    ],
)
def test_migrate_to_time_period(
    old: object,
    new: tuple[Literal["cmk_postprocessed"], Literal["stored_time_period"], str],
) -> None:
    assert migrate_to_time_period(old) == new
    assert migrate_to_time_period(new) == new
