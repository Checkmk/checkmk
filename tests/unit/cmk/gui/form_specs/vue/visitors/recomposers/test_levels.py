#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal, TypeVar

import pytest

from cmk.utils.user import UserId

from cmk.gui.form_specs.vue.form_spec_visitor import (
    serialize_data_for_frontend,
    transform_to_disk_model,
)
from cmk.gui.form_specs.vue.visitors import DataOrigin, DEFAULT_VALUE
from cmk.gui.session import UserContext

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    InputHint,
    LevelDirection,
    Levels,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    PredictiveLevels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    TimeMagnitude,
    TimeSpan,
)

_NumberT = TypeVar("_NumberT", int, float)
_LevelsFormSpecModel = SimpleLevelsConfigModel[_NumberT] | tuple[Literal["predictive"], object]


def levels_spec() -> Levels:
    return Levels[float](
        title=Title("Levels"),
        form_spec_template=Percentage(),
        level_direction=LevelDirection.LOWER,
        prefill_fixed_levels=DefaultValue((13.0, 23.0)),
        predictive=PredictiveLevels(
            reference_metric="foo",
            prefill_abs_diff=DefaultValue((10.0, 20.0)),
        ),
        prefill_levels_type=DefaultValue(LevelsType.NONE),
    )


@pytest.mark.parametrize(
    ["spec", "value", "expected_frontend_data", "expected_disk_data"],
    [
        pytest.param(
            Levels[float](
                title=Title("Levels"),
                form_spec_template=Percentage(),
                level_direction=LevelDirection.LOWER,
                prefill_fixed_levels=DefaultValue((13.0, 23.0)),
                predictive=PredictiveLevels(
                    reference_metric="foo",
                    prefill_abs_diff=DefaultValue((10.0, 20.0)),
                ),
                prefill_levels_type=DefaultValue(LevelsType.NONE),
            ),
            DEFAULT_VALUE,
            ("no_levels", None),
            ("no_levels", None),
        ),
        pytest.param(
            Levels[float](
                title=Title("Levels"),
                form_spec_template=Percentage(),
                level_direction=LevelDirection.LOWER,
                prefill_fixed_levels=DefaultValue((13.0, 23.0)),
                predictive=PredictiveLevels(
                    reference_metric="foo",
                    prefill_abs_diff=DefaultValue((10.0, 20.0)),
                ),
                prefill_levels_type=DefaultValue(LevelsType.FIXED),
            ),
            DEFAULT_VALUE,
            ("fixed", [13.0, 23.0]),
            ("fixed", (13.0, 23.0)),
        ),
        pytest.param(
            Levels[float](
                title=Title("Levels"),
                form_spec_template=Percentage(),
                level_direction=LevelDirection.LOWER,
                prefill_fixed_levels=DefaultValue((13.0, 23.0)),
                predictive=PredictiveLevels(
                    reference_metric="foo",
                    prefill_abs_diff=DefaultValue((10.0, 20.0)),
                ),
                prefill_levels_type=DefaultValue(LevelsType.PREDICTIVE),
            ),
            DEFAULT_VALUE,
            (
                "predictive",
                {
                    "period": "6c47c99835b507ae0ddffd0df817fbdd30633b902a75e5296b3a9c01417c2ec2",
                    "horizon": 90,
                    "levels": ("absolute", [10.0, 20.0]),
                    "bound": None,
                },
            ),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "period": "wday",
                    "horizon": 90,
                    "levels": ("absolute", (10.0, 20.0)),
                    "bound": None,
                },
            ),
        ),
        pytest.param(
            levels_spec(),
            ("no_levels", None),
            ("no_levels", None),
            ("no_levels", None),
        ),
        pytest.param(
            levels_spec(),
            ("fixed", (30, 20)),
            ("fixed", [30, 20]),
            ("fixed", (30, 20)),
        ),
        pytest.param(
            levels_spec(),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "period": "wday",
                    "horizon": 90,
                    "levels": ("absolute", (10.0, 20.0)),
                    "bound": None,
                },
            ),
            (
                "predictive",
                {
                    "period": "6c47c99835b507ae0ddffd0df817fbdd30633b902a75e5296b3a9c01417c2ec2",
                    "horizon": 90,
                    "levels": ("absolute", [10.0, 20.0]),
                    "bound": None,
                },
            ),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "period": "wday",
                    "horizon": 90,
                    "levels": ("absolute", (10.0, 20.0)),
                    "bound": None,
                },
            ),
        ),
        pytest.param(
            levels_spec(),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "period": "day",
                    "horizon": 3,
                    "levels": ("stdev", (10.0, 20.0)),
                    "bound": None,
                },
            ),
            (
                "predictive",
                {
                    "period": "4473bc8a7aa356e29acba007e36b0c1a020aecf9a2bd2abdd653149148d02281",
                    "horizon": 3,
                    "levels": ("stdev", [10.0, 20.0]),
                    "bound": None,
                },
            ),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "period": "day",
                    "horizon": 3,
                    "levels": ("stdev", (10.0, 20.0)),
                    "bound": None,
                },
            ),
        ),
    ],
)
def test_levels_recompose(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    spec: Levels,
    value: Any,
    expected_frontend_data: tuple[str, Any],
    expected_disk_data: _LevelsFormSpecModel,
) -> None:
    """Gets a spec and its value, serializes it for the frontend
    and then parses it back to disk data."""
    with UserContext(with_user[0]):
        vue_app_config = serialize_data_for_frontend(
            spec,
            "ut_id",
            DataOrigin.DISK,
            do_validate=True,
            value=value,
        )

        assert len(vue_app_config.validation) == 0
        frontend_data = vue_app_config.data
        disk_data = transform_to_disk_model(spec, frontend_data)
        assert frontend_data == expected_frontend_data
        assert disk_data == expected_disk_data


@pytest.mark.parametrize(
    ["spec", "invalid_value", "expected_validation_message"],
    [
        pytest.param(
            levels_spec(),
            (
                "foo",
                "predictive_levels",
                {
                    "period": "day",
                    "horizon": 3,
                    "levels": ("nonsense", (10.0, 20.0)),
                    "bound": None,
                },
            ),
            "Unable to transform value",
        ),
        pytest.param(
            levels_spec(),
            (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    "period": "day",
                    "horizon": 3,
                    "levels": ("nonsense", (10.0, 20.0)),
                    "bound": None,
                },
            ),
            "Invalid selection",
        ),
    ],
)
def test_levels_recompose_invalid_data(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    spec: Levels,
    invalid_value: Any,
    expected_validation_message: str,
) -> None:
    with UserContext(with_user[0]):
        vue_app_config = serialize_data_for_frontend(
            spec,
            "ut_id",
            DataOrigin.DISK,
            do_validate=True,
            value=invalid_value,
        )

        assert len(vue_app_config.validation) == 1
        assert vue_app_config.validation[0].message == expected_validation_message


def test_simple_levels_migrate_from_legacy_milliseconds(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
) -> None:
    """Regression test: SimpleLevels.migrate must be preserved through recompose().

    Old 2.3 rules store response_time as a raw (warn_ms, crit_ms) tuple.
    The migration function scales by 0.001 to convert ms → seconds for TimeSpan.
    Without the fix (migrate=form_spec.migrate missing in recompose()), the migration
    is silently dropped and _transform_from_disk raises ValueError on the old tuple."""
    spec = SimpleLevels[float](
        title=Title("Expected response time"),
        level_direction=LevelDirection.UPPER,
        form_spec_template=TimeSpan(displayed_magnitudes=(TimeMagnitude.MILLISECOND,)),
        prefill_fixed_levels=InputHint((0.1, 0.2)),
        migrate=lambda v: migrate_to_float_simple_levels(v, 0.001),
    )

    with UserContext(with_user[0]):
        # Old 2.3 format: tuple of (warn_ms, crit_ms)
        vue_app_config = serialize_data_for_frontend(
            spec,
            "ut_id",
            DataOrigin.DISK,
            do_validate=True,
            value=(1000.0, 2000.0),
        )

    assert len(vue_app_config.validation) == 0
    assert vue_app_config.data == ("fixed", [1.0, 2.0])
