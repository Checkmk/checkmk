#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.lib import cpu_util


def test_check_cpu_util() -> None:
    """
    Test a quite straight forward case. Nothing in particular, just to have at least any test.
    """

    value_store: dict[str, Any] = {}

    assert list(
        cpu_util.check_cpu_util(
            value_store=value_store,
            util=123.0,
            params={
                "average": 3.0,
                "levels": (80.0, 90.0),
                "levels_single": (12.0, 13.0),
            },
            this_time=0.0,  # Jan 1 1970 (who cares)
            cores=[
                ("my_core", 12.0),
                ("your_core", 42.0),
            ],
            perf_max=200.0,
        )
    ) == [
        Metric("util", 123.0, levels=(80.0, 90.0), boundaries=(0.0, 200.0)),
        Result(
            state=State.CRIT,
            summary="Total CPU (3 min average): 123.00% (warn/crit at 80.00%/90.00%)",
        ),
        Metric("util_average", 123.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
        Result(
            state=State.WARN,
            notice="Core my_core: 12.00% (warn/crit at 12.00%/13.00%)",
        ),
        Result(
            state=State.CRIT,
            notice="Core your_core: 42.00% (warn/crit at 12.00%/13.00%)",
        ),
    ]


def test_check_cpu_util_unix() -> None:
    assert list(
        cpu_util.check_cpu_util_unix(
            cpu_info=cpu_util.CPUInfo("cpu-name", 10, 4, 6, 8, 5, 8, 3, 6, 2, 4),
            params={},
            this_time=0,
            value_store={},
            cores=[],
            values_counter=False,
        )
    ) == [
        Result(state=State.OK, notice="User: 10.00%"),
        Metric("user", 10.0),
        Result(state=State.OK, notice="System: 6.00%"),
        Metric("system", 6.0),
        Result(state=State.OK, notice="Wait: 5.00%"),
        Metric("wait", 5.0),
        Result(state=State.OK, notice="Steal: 6.00%"),
        Metric("steal", 6.0),
        Result(state=State.OK, notice="Guest: 2.00%"),
        Metric("guest", 2.0),
        Result(state=State.OK, summary="Total CPU: 42.00%"),
        Metric("util", 42.0, boundaries=(0.0, None)),
    ]


@pytest.mark.parametrize(
    [
        "first_timestamp",
        "second_timestamp",
        "usage",
        "threshold",
        "levels",
        "expected_result",
    ],
    [
        pytest.param(
            23,
            30,
            24,
            40,
            (5, 10),
            [],
            id="below threshold",
        ),
        pytest.param(
            15,
            50,
            100,
            100,
            (13, 23),
            [
                Result(
                    state=State.CRIT,
                    summary="my_core is under high load for: 35 seconds (warn/crit at 13 seconds/23 seconds)",
                ),
            ],
            id="at threshold",
        ),
        pytest.param(
            23,
            30,
            42,
            40,
            (5, 10),
            [
                Result(
                    state=State.WARN,
                    summary="my_core is under high load for: 7 seconds (warn/crit at 5 seconds/10 seconds)",
                )
            ],
            id="above threshold",
        ),
    ],
)
def test_cpu_util_time(
    first_timestamp: float,
    second_timestamp: float,
    usage: float,
    threshold: float,
    levels: tuple[float, float],
    expected_result: CheckResult,
) -> None:
    value_store: dict[str, object] = {}
    # fill value store
    assert not list(
        cpu_util._cpu_util_time(
            this_time=first_timestamp,
            core="my_core",
            perc=usage,
            threshold=threshold,
            levels=levels,
            value_store=value_store,
        )
    )
    # produce result if threshold is exceeded
    assert (
        list(
            cpu_util._cpu_util_time(
                this_time=second_timestamp,
                core="my_core",
                perc=usage,
                threshold=threshold,
                levels=levels,
                value_store=value_store,
            )
        )
        == expected_result
    )


def test__util_counter() -> None:
    cpu = cpu_util.CPUInfo("cpu-name", 100, 40, 60, 80, 50, 80, 30, 60, 20, 40)

    assert cpu_util._util_counter(cpu, {}) == cpu

    assert cpu_util._util_counter(
        cpu,
        {
            "cpu.util.user": 20,
            "cpu.util.system": 10,
            "cpu.util.idle": 5,
        },
    ) == cpu_util.CPUInfo("cpu-name", 80, 40, 50, 75, 50, 80, 30, 60, 20, 40)
