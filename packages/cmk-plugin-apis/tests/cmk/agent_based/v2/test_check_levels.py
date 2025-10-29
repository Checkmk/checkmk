#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence

import pytest

from cmk.agent_based.v2 import Metric, render, Result, State
from cmk.agent_based.v2._check_levels import (
    _check_levels,
    _check_predictive_levels,
    _default_rendering,
    _summarize_predictions,
    check_levels,
    CheckLevelsResult,
    Direction,
    FixedLevelsT,
    LevelsT,
    NoLevelsT,
    Type,
)


def test_check_predictive_levels() -> None:
    result = _check_predictive_levels(
        5.0, "metric", None, None, Direction.UPPER, _default_rendering
    )
    assert result == CheckLevelsResult(Type.PREDICTIVE, State.OK)


@pytest.mark.parametrize(
    "value, levels, expected_result",
    [
        pytest.param(
            5.0,
            None,
            CheckLevelsResult(
                type=Type.NO_LEVELS,
                state=State.OK,
                levels=None,
                levels_text="",
                prediction=None,
            ),
            id="levels not provided",
        ),
        pytest.param(
            5.0,
            ("no_levels", None),
            CheckLevelsResult(
                type=Type.NO_LEVELS,
                state=State.OK,
                levels=None,
                levels_text="",
                prediction=None,
            ),
            id="no_levels",
        ),
        pytest.param(
            5.0,
            ("fixed", (3.0, 4.0)),
            CheckLevelsResult(
                type=Type.FIXED,
                state=State.CRIT,
                levels=(3.0, 4.0),
                levels_text="(warn/crit at 3.00/4.00)",
                prediction=None,
            ),
            id="fixed levels",
        ),
        pytest.param(
            5.0,
            ("predictive", ("test_metric", 4.5, (5.0, 6.0))),
            CheckLevelsResult(
                type=Type.PREDICTIVE,
                state=State.WARN,
                levels=(5.0, 6.0),
                levels_text="(warn/crit at 5.00/6.00)",
                prediction=Metric("predict_test_metric", 4.5),
            ),
            id="predictive levels",
        ),
    ],
)
def test__check_levels(
    value: float,
    levels: LevelsT[float] | None,
    expected_result: CheckLevelsResult,
) -> None:
    result = _check_levels(value, levels, Direction.UPPER, _default_rendering)
    assert result == expected_result


@pytest.mark.parametrize(
    "value, levels, error_type, error_message",
    [
        pytest.param(
            5.0,
            ("unknown", 3.0),
            TypeError,
            "Incorrect level parameters",
            id="invalid level type",
        ),
        pytest.param(
            5.0,
            ("fixed", 3.0),
            TypeError,
            "Incorrect level parameters",
            id="invalid fixed levels",
        ),
        pytest.param(
            5.0,
            ("predictive", 3.0),
            TypeError,
            "Incorrect level parameters",
            id="invalid predictive levels",
        ),
    ],
)
def test__check_levels_errors(
    value: float,
    levels: LevelsT[float] | None,
    error_type: type[Exception],
    error_message: str,
) -> None:
    with pytest.raises(error_type, match=error_message):
        _check_levels(value, levels, Direction.UPPER, _default_rendering)


@pytest.mark.parametrize(
    "upper_result, lower_result, expected_result",
    [
        pytest.param(
            CheckLevelsResult(Type.FIXED, State.WARN, (6.0, 7.0), "(warn/crit at 6.00/7.00)", None),
            CheckLevelsResult(Type.NO_LEVELS, State.OK),
            ((), ""),
            id="no predictive levels",
        ),
        pytest.param(
            CheckLevelsResult(Type.FIXED, State.WARN, (6.0, 7.0), "(warn/crit at 6.00/7.00)", None),
            CheckLevelsResult(
                Type.PREDICTIVE,
                State.OK,
                (2.0, 1.0),
                "",
                Metric("predict_test_metric", 6.5),
            ),
            (
                [
                    Metric("predict_test_metric", 6.5),
                ],
                "(prediction: 6.50%)",
            ),
            id="1 direction predictive levels",
        ),
        pytest.param(
            CheckLevelsResult(
                Type.PREDICTIVE,
                State.WARN,
                (6.0, 7.0),
                "(warn/crit at 6.00/7.00)",
                Metric("predict_test_metric", 6.5),
            ),
            CheckLevelsResult(
                Type.PREDICTIVE,
                State.OK,
                (2.0, 1.0),
                "",
                Metric("predict_lower_test_metric", 6.5),
            ),
            (
                [
                    Metric("predict_test_metric", 6.5),
                    Metric("predict_lower_test_metric", 6.5),
                ],
                "(prediction: 6.50%)",
            ),
            id="2 directions predictive levels, same predictions",
        ),
        pytest.param(
            CheckLevelsResult(
                Type.PREDICTIVE,
                State.WARN,
                (6.0, 7.0),
                "(warn/crit at 6.00/7.00)",
                Metric("predict_test_metric", 6.5),
            ),
            CheckLevelsResult(
                Type.PREDICTIVE,
                State.OK,
                (2.0, 1.0),
                "",
                Metric("predict_lower_test_metric", 3.0),
            ),
            (
                [
                    Metric("predict_test_metric", 6.5),
                    Metric("predict_lower_test_metric", 3.0),
                ],
                "(upper levels prediction: 6.50%, lower levels prediction: 3.00%)",
            ),
            id="2 directions predictive levels, different predictions",
        ),
        pytest.param(
            CheckLevelsResult(
                Type.PREDICTIVE,
                State.OK,
            ),
            CheckLevelsResult(Type.PREDICTIVE, State.OK),
            ((), "(prediction: N/A)"),
            id="2 directions predictive levels, no predictions",
        ),
    ],
)
def test_summarize_predictions(
    upper_result: CheckLevelsResult,
    lower_result: CheckLevelsResult,
    expected_result: tuple[Sequence[Metric], str],
) -> None:
    result = _summarize_predictions(
        upper_result=upper_result,
        lower_result=lower_result,
        render_func=render.percent,
    )
    assert result == expected_result


@pytest.mark.parametrize(
    "value, levels_upper, levels_lower, render_function, label, boundaries,"
    "notice_only, expected_results",
    [
        pytest.param(
            10.0,
            None,
            None,
            None,
            None,
            None,
            True,
            [Result(state=State.OK, notice="10.00")],
            id="only required parameter",
        ),
        pytest.param(
            9.0,
            ("fixed", (7.0, 8.0)),
            ("fixed", (10.0, 2.0)),
            None,
            None,
            None,
            False,
            [
                Result(
                    state=State.CRIT,
                    summary="9.00 (warn/crit at 7.00/8.00) (warn/crit below 10.00/2.00)",
                )
            ],
            id="levels overlap",
        ),
    ],
)
def test_check_levels(
    value: float,
    levels_upper: NoLevelsT | FixedLevelsT[float] | None,
    levels_lower: NoLevelsT | FixedLevelsT[float] | None,
    render_function: Callable[[float], str] | None,
    label: str | None,
    boundaries: tuple[float | None, float | None] | None,
    notice_only: bool,
    expected_results: Sequence[Result | Metric],
) -> None:
    results = list(
        check_levels(
            value,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=None,
            render_func=render_function,
            label=label,
            boundaries=boundaries,
            notice_only=notice_only,
        )
    )

    assert results == expected_results


@pytest.mark.parametrize(
    "value, levels_upper, levels_lower, metric_name, render_function,"
    "label, boundaries, notice_only, expected_results",
    [
        pytest.param(
            5.0,
            ("no_levels", None),
            ("fixed", (6.0, 3.0)),
            "test_metric",
            render.percent,
            "test label",
            (0.0, 10.0),
            True,
            [
                Result(
                    state=State.WARN,
                    summary="test label: 5.00% (warn/crit below 6.00%/3.00%)",
                ),
                Metric("test_metric", 5.0, boundaries=(0.0, 10.0)),
            ],
            id="all params are present",
        ),
        pytest.param(
            9.0,
            (
                "predictive",
                ("reference_metric", 4.5, (5.0, 6.0)),
            ),
            ("fixed", (12.0, 10.0)),
            "test_metric",
            None,
            None,
            None,
            False,
            [
                Result(
                    state=State.CRIT,
                    summary="9.00 (prediction: 4.50) (warn/crit at 5.00/6.00)"
                    " (warn/crit below 12.00/10.00)",
                ),
                Metric("test_metric", 9.0, levels=(5.0, 6.0)),
                Metric("predict_reference_metric", 4.5),
            ],
            id="levels overlap",
        ),
        pytest.param(
            5.0,
            ("no_levels", None),
            ("fixed", (2.0, 1.0)),
            "test_metric",
            None,
            None,
            None,
            False,
            [Result(state=State.OK, summary="5.00"), Metric("test_metric", 5.0)],
            id="OK state",
        ),
    ],
)
def test_check_levels_with_metric(
    value: float,
    levels_upper: LevelsT[float] | None,
    levels_lower: LevelsT[float] | None,
    metric_name: str,
    render_function: Callable[[float], str] | None,
    label: str | None,
    boundaries: tuple[float | None, float | None] | None,
    notice_only: bool,
    expected_results: Sequence[Result | Metric],
) -> None:
    results = list(
        check_levels(
            value,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=metric_name,
            render_func=render_function,
            label=label,
            boundaries=boundaries,
            notice_only=notice_only,
        )
    )

    assert results == expected_results
