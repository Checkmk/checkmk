#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections.abc import Sequence
from typing import Callable

import pytest

import cmk.agent_based.v2._check_levels
from cmk.agent_based.prediction_backend import (
    _Direction,
    _EstimatedLevels,
    _Prediction,
    InjectedParameters,
    PredictionParameters,
)
from cmk.agent_based.v2 import Metric, render, Result, State
from cmk.agent_based.v2._check_levels import (
    _check_levels,
    _check_predictive_levels,
    _default_rendering,
    _FixedLevels,
    _NoLevels,
    _PredictiveLevels,
    _PredictiveModel,
    _summarize_predictions,
    check_levels,
    CheckLevelsResult,
    Direction,
    Type,
)


def mock_lookup_predictive_levels(
    _metric: str,
    _direction: _Direction,
    _parameters: PredictionParameters,
    _injected: InjectedParameters,
) -> tuple[_Prediction | None, _EstimatedLevels | None]:
    return (6.5, (5.0, 6.0))


def mock_lookup_predictive_levels_empty(
    _metric: str,
    _direction: _Direction,
    _parameters: PredictionParameters,
    _injected: InjectedParameters,
) -> tuple[_Prediction | None, _EstimatedLevels | None]:
    return (None, None)


def test_check_predictive_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.agent_based.v2._check_levels,  # pylint: disable=protected-access
        "lookup_predictive_levels",
        mock_lookup_predictive_levels_empty,
    )
    levels_params: _PredictiveModel = {
        "period": "hour",
        "horizon": 90,
        "levels": ("relative", (3.0, 4.0)),
        "__injected__": {"meta_file_path_template": "path_template", "predictions": {}},
    }
    result = _check_predictive_levels(
        5.0, levels_params, Direction.UPPER, "test_metric", _default_rendering
    )
    assert result == CheckLevelsResult(Type.PREDICTIVE, State.OK)


@pytest.mark.parametrize(
    "value, levels, metric_name, expected_result",
    [
        pytest.param(
            5.0,
            None,
            None,
            CheckLevelsResult(
                type=Type.NO_LEVELS, state=State.OK, levels=None, levels_text="", prediction=None
            ),
            id="levels not provided",
        ),
        pytest.param(
            5.0,
            ("no_levels", None),
            None,
            CheckLevelsResult(
                type=Type.NO_LEVELS, state=State.OK, levels=None, levels_text="", prediction=None
            ),
            id="no_levels",
        ),
        pytest.param(
            5.0,
            ("fixed", (3.0, 4.0)),
            None,
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
            (
                "predictive",
                {
                    "period": "hour",
                    "horizon": 90,
                    "levels": ("relative", (3.0, 4.0)),
                    "__injected__": {"meta_file_path_template": "path_template", "predictions": {}},
                },
            ),
            "test_metric",
            CheckLevelsResult(
                type=Type.PREDICTIVE,
                state=State.WARN,
                levels=(5.0, 6.0),
                levels_text="(warn/crit at 5.00/6.00)",
                prediction=Metric("predict_test_metric", 6.5),
            ),
            id="predictive levels",
        ),
    ],
)
def test__check_levels(
    value: float,
    levels: _NoLevels | _FixedLevels | _PredictiveLevels | None,
    metric_name: str | None,
    expected_result: CheckLevelsResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.agent_based.v2._check_levels,  # pylint: disable=protected-access
        "lookup_predictive_levels",
        mock_lookup_predictive_levels,
    )
    result = _check_levels(value, levels, Direction.UPPER, _default_rendering, metric_name)
    assert result == expected_result


@pytest.mark.parametrize(
    "value, levels, metric_name, error_type, error_message",
    [
        pytest.param(
            5.0,
            ("unknown", 3.0),
            "test_metric",
            AssertionError,
            "Expected code to be unreachable, but got: 'unknown'",
            id="invalid level type",
        ),
        pytest.param(
            5.0,
            ("fixed", 3.0),
            "test_metric",
            TypeError,
            "Incorrect level parameters",
            id="invalid fixed levels",
        ),
        pytest.param(
            5.0,
            ("predictive", {}),
            None,
            TypeError,
            "Metric name can't be `None` if predictive levels are used.",
            id="predictive levels without metric",
        ),
        pytest.param(
            5.0,
            ("predictive", 3.0),
            "test_metric",
            TypeError,
            "Incorrect level parameters",
            id="invalid predictive levels",
        ),
    ],
)
def test__check_levels_errors(
    value: float,
    levels: _NoLevels | _FixedLevels | _PredictiveLevels | None,
    metric_name: str | None,
    error_type: typing.Type[Exception],
    error_message: str,
) -> None:
    with pytest.raises(error_type, match=error_message):
        _check_levels(value, levels, Direction.UPPER, _default_rendering, metric_name)


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
                Type.PREDICTIVE, State.OK, (2.0, 1.0), "", Metric("predict_test_metric", 6.5)
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
                Type.PREDICTIVE, State.OK, (2.0, 1.0), "", Metric("predict_lower_test_metric", 6.5)
            ),
            (
                [Metric("predict_test_metric", 6.5), Metric("predict_lower_test_metric", 6.5)],
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
                Type.PREDICTIVE, State.OK, (2.0, 1.0), "", Metric("predict_lower_test_metric", 3.0)
            ),
            (
                [Metric("predict_test_metric", 6.5), Metric("predict_lower_test_metric", 3.0)],
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
def test_check_levels(  # pylint: disable=too-many-arguments
    value: float,
    levels_upper: _NoLevels | _FixedLevels | None,
    levels_lower: _NoLevels | _FixedLevels | None,
    render_function: Callable[[float], str] | None,
    label: str | None,
    boundaries: tuple[float | None, float | None] | None,
    notice_only: bool,
    expected_results: Sequence[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.agent_based.v2._check_levels,  # pylint: disable=protected-access
        "lookup_predictive_levels",
        mock_lookup_predictive_levels,
    )
    results = list(
        check_levels(
            value,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=None,
            render_function=render_function,
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
                Result(state=State.WARN, summary="test label: 5.00% (warn/crit below 6.00%/3.00%)"),
                Metric("test_metric", 5.0, boundaries=(0.0, 10.0)),
            ],
            id="all params are present",
        ),
        pytest.param(
            9.0,
            (
                "predictive",
                {
                    "period": "hour",
                    "horizon": 90,
                    "levels": ("relative", (3.0, 4.0)),
                    "__injected__": {"meta_file_path_template": "path_template", "predictions": {}},
                },
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
                    summary="9.00 (prediction: 6.50) (warn/crit at 5.00/6.00)"
                    " (warn/crit below 12.00/10.00)",
                ),
                Metric("test_metric", 9.0, levels=(5.0, 6.0)),
                Metric("predict_test_metric", 6.5),
            ],
            id="levels overlap",
        ),
        pytest.param(
            5.0,
            ("no_levels", (12.0, 10.0)),
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
def test_check_levels_with_metric(  # pylint: disable=too-many-arguments
    value: float,
    levels_upper: _NoLevels | _FixedLevels | _PredictiveLevels | None,
    levels_lower: _NoLevels | _FixedLevels | _PredictiveLevels | None,
    metric_name: str,
    render_function: Callable[[float], str] | None,
    label: str | None,
    boundaries: tuple[float | None, float | None] | None,
    notice_only: bool,
    expected_results: Sequence[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.agent_based.v2._check_levels,  # pylint: disable=protected-access
        "lookup_predictive_levels",
        mock_lookup_predictive_levels,
    )
    results = list(
        check_levels(
            value,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=metric_name,
            render_function=render_function,
            label=label,
            boundaries=boundaries,
            notice_only=notice_only,
        )
    )

    assert results == expected_results
