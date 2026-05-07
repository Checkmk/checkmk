#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v3_unstable import check_levels, Metric, Result, State


def _results(
    value: float,
    **kwargs: object,
) -> list[Result | Metric]:
    return list(check_levels(value, **kwargs))  # type: ignore[arg-type]


def test_no_metric_no_levels() -> None:
    (result,) = _results(5.0)
    assert isinstance(result, Result)
    assert result.state is State.OK
    assert result.summary == "5.00"


def test_no_metric_with_label() -> None:
    (result,) = _results(5.0, label="Temp")
    assert isinstance(result, Result)
    assert result.summary == "Temp: 5.00"


def test_upper_levels_warn() -> None:
    (result,) = _results(8.0, levels_upper=("fixed", (5.0, 10.0)))
    assert isinstance(result, Result)
    assert result.state is State.WARN


def test_upper_levels_crit() -> None:
    (result,) = _results(11.0, levels_upper=("fixed", (5.0, 10.0)))
    assert isinstance(result, Result)
    assert result.state is State.CRIT


def test_lower_levels_warn() -> None:
    (result,) = _results(3.0, levels_lower=("fixed", (5.0, 1.0)))
    assert isinstance(result, Result)
    assert result.state is State.WARN


def test_lower_levels_crit() -> None:
    (result,) = _results(0.5, levels_lower=("fixed", (5.0, 1.0)))
    assert isinstance(result, Result)
    assert result.state is State.CRIT


def test_metric_carries_upper_levels() -> None:
    result, metric = _results(
        8.0,
        levels_upper=("fixed", (5.0, 10.0)),
        metric_name="temp",
    )
    assert isinstance(metric, Metric)
    assert metric.levels == (5.0, 10.0)
    assert metric.lower_levels == (None, None)


def test_metric_carries_lower_levels() -> None:
    result, metric = _results(
        8.0,
        levels_lower=("fixed", (3.0, 1.0)),
        metric_name="temp",
    )
    assert isinstance(metric, Metric)
    assert metric.lower_levels == (3.0, 1.0)
    assert metric.levels == (None, None)


def test_metric_carries_both_levels() -> None:
    result, metric = _results(
        8.0,
        levels_upper=("fixed", (10.0, 20.0)),
        levels_lower=("fixed", (3.0, 1.0)),
        metric_name="temp",
    )
    assert isinstance(metric, Metric)
    assert metric.levels == (10.0, 20.0)
    assert metric.lower_levels == (3.0, 1.0)


def test_metric_no_lower_levels_when_not_specified() -> None:
    result, metric = _results(
        8.0,
        levels_upper=("fixed", (10.0, 20.0)),
        metric_name="temp",
    )
    assert isinstance(metric, Metric)
    assert metric.lower_levels == (None, None)


def test_metric_with_boundaries() -> None:
    result, metric = _results(
        50.0,
        metric_name="usage",
        boundaries=(0.0, 100.0),
    )
    assert isinstance(metric, Metric)
    assert metric.boundaries == (0.0, 100.0)


def test_no_levels_type() -> None:
    result, metric = _results(
        8.0,
        levels_upper=("no_levels", None),
        levels_lower=("no_levels", None),
        metric_name="temp",
    )
    assert isinstance(result, Result)
    assert result.state is State.OK
    assert isinstance(metric, Metric)
    assert metric.levels == (None, None)
    assert metric.lower_levels == (None, None)


def test_notice_only_ok_hides_summary() -> None:
    (result,) = _results(1.0, levels_upper=("fixed", (5.0, 10.0)), notice_only=True)
    assert isinstance(result, Result)
    assert result.state is State.OK
    assert result.summary == ""
    assert result.details == "1.00"


def test_notice_only_non_ok_shows_summary() -> None:
    (result,) = _results(8.0, levels_upper=("fixed", (5.0, 10.0)), notice_only=True)
    assert isinstance(result, Result)
    assert result.state is State.WARN
    assert "warn/crit" in result.summary


@pytest.mark.parametrize(
    "value, levels_upper, levels_lower, expected_state",
    [
        (5.0, ("fixed", (10.0, 20.0)), ("fixed", (1.0, 0.5)), State.OK),
        (15.0, ("fixed", (10.0, 20.0)), ("fixed", (1.0, 0.5)), State.WARN),
        (25.0, ("fixed", (10.0, 20.0)), ("fixed", (1.0, 0.5)), State.CRIT),
        (0.8, ("fixed", (10.0, 20.0)), ("fixed", (1.0, 0.5)), State.WARN),
        (0.3, ("fixed", (10.0, 20.0)), ("fixed", (1.0, 0.5)), State.CRIT),
    ],
)
def test_state_combinations(
    value: float,
    levels_upper: object,
    levels_lower: object,
    expected_state: State,
) -> None:
    result, _metric = _results(
        value,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        metric_name="val",
    )
    assert isinstance(result, Result)
    assert result.state is expected_state
