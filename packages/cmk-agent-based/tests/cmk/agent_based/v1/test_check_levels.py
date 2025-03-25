#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable

import pytest

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import Metric, render, Result, State
from cmk.agent_based.v1._check_levels import _do_check_levels as do_check_levels


def _format_float(x: float) -> str:
    return f"{x:.1f}"


def _format_meter(x: float) -> str:
    return f"{x:.1f} m"


@pytest.mark.parametrize(
    "value, levels_upper, levels_lower, render_func, result",
    [
        (5, (3, 6), None, int, (State.WARN, " (warn/crit at 3/6)")),
        (7, (3, 6), None, _format_meter, (State.CRIT, " (warn/crit at 3.0 m/6.0 m)")),
        (7, (3, 6), None, _format_float, (State.CRIT, " (warn/crit at 3.0/6.0)")),
        (2, (3, 6), (1, 0), int, (State.OK, "")),
        (1, (3, 6), (1, 0), int, (State.OK, "")),
        (0, (3, 6), (1, 0), int, (State.WARN, " (warn/crit below 1/0)")),
        (-1, (3, 6), (1, 0), int, (State.CRIT, " (warn/crit below 1/0)")),
    ],
)
def test_boundaries(
    value: float,
    levels_upper: tuple[float, float] | None,
    levels_lower: tuple[float, float] | None,
    render_func: Callable[[float], str],
    result: tuple[State, str],
) -> None:
    assert do_check_levels(value, levels_upper, levels_lower, render_func) == result


def test_check_levels_wo_levels() -> None:
    assert list(check_levels_v1(5, metric_name="battery", render_func=render.percent)) == [
        Result(state=State.OK, summary="5.00%"),
        Metric("battery", 5.0),
    ]


def test_check_levels_ok_levels() -> None:
    assert list(
        check_levels_v1(
            5, metric_name="battery", render_func=render.percent, levels_upper=(100, 200)
        )
    ) == [
        Result(state=State.OK, summary="5.00%"),
        Metric("battery", 5.0, levels=(100.0, 200.0)),
    ]


def test_check_levels_warn_levels() -> None:
    def _format_years(x: float) -> str:
        return f"{x:.2f} years"

    assert list(
        check_levels_v1(
            6,
            metric_name="disk",
            levels_upper=(4, 8),
            render_func=_format_years,
            label="Disk Age",
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Disk Age: 6.00 years (warn/crit at 4.00 years/8.00 years)",
        ),
        Metric("disk", 6.0, levels=(4.0, 8.0)),
    ]


def test_check_levels_boundaries() -> None:
    def _format_ph(x: float) -> str:
        return f"pH {-math.log10(x):.1f}"

    assert list(
        check_levels_v1(
            5e-7,
            metric_name="H_concentration",
            levels_upper=(4e-7, 8e-7),
            levels_lower=(5e-8, 2e-8),
            render_func=_format_ph,
            label="Water acidity",
            boundaries=(0, None),
        )
    ) == [
        Result(state=State.WARN, summary="Water acidity: pH 6.3 (warn/crit at pH 6.4/pH 6.1)"),
        Metric("H_concentration", 5e-7, levels=(4e-7, 8e-7), boundaries=(0, None)),
    ]
