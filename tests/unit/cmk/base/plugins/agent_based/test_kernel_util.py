#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import freezegun
import pytest

from cmk.base.plugins.agent_based import kernel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

SECTION: kernel.Section = (
    11238,
    {
        "Context Switches": [("ctxt", 539210403)],
        "Cpu Utilization": [
            (
                "cpu",
                [
                    "13008772",
                    "12250",
                    "5234590",
                    "181918601",
                    "73242",
                    "0",
                    "524563",
                    "0",
                    "0",
                    "0",
                ],
            ),
            (
                "cpu0",
                [
                    "1602366",
                    "1467",
                    "675813",
                    "22730303",
                    "9216",
                    "0",
                    "265437",
                    "0",
                    "0",
                    "0",
                ],
            ),
            (
                "cpu1",
                [
                    "1463624",
                    "1624",
                    "576516",
                    "22975174",
                    "8376",
                    "0",
                    "116908",
                    "0",
                    "0",
                    "0",
                ],
            ),
        ],
        "Major Page Faults": [("pgmajfault", 1795031)],
        "Page Swap Out": [("pswpout", 751706)],
        "Page Swap in": [("pswpin", 250829)],
        "Process Creations": [("processes", 4700038)],
    },
)

BASIC_RESULT = [
    Result(state=State.OK, notice="User: 6.49%"),
    Metric("user", 6.48547647710549),
    Result(state=State.OK, notice="System: 2.87%"),
    Metric("system", 2.868503817100648),
    Result(state=State.OK, notice="Wait: 0.04%"),
    Metric("wait", 0.03648018320959447),
    Result(state=State.OK, summary="Total CPU: 9.39%"),
    Metric("util", 9.390460477415733, boundaries=(0.0, None)),
]

CORE_RESULT = [
    Result(state=State.OK, notice="Core cpu0: 2.54%"),
    Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
    Result(state=State.OK, notice="Core cpu1: 2.16%"),
    Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
]


def test_discovery() -> None:
    assert list(kernel.discover_kernel_util(SECTION)) == [
        Service(),
    ]


@pytest.mark.parametrize(
    "parameters, additional_results",
    [
        ({}, []),
        (
            {"levels_single": (80, 90)},
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
            ],
        ),
        (
            {"levels_single": (1, 5)},
            [
                Result(state=State.WARN, notice="Core cpu0: 2.54% (warn/crit at 1.00%/5.00%)"),
                Result(state=State.WARN, notice="Core cpu1: 2.16% (warn/crit at 1.00%/5.00%)"),
            ],
        ),
        (
            {"core_util_graph": True},
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048),
            ],
        ),
        (
            {"core_util_time": (1, 1, 2)},
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
            ],
        ),
        (
            {"levels_single": (80, 90), "core_util_graph": True},
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855, levels=(80.0, 90.0)),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048, levels=(80.0, 90.0)),
            ],
        ),
        (
            {"levels_single": (1, 5), "core_util_graph": True},
            [
                Result(state=State.WARN, summary="Core cpu0: 2.54% (warn/crit at 1.00%/5.00%)"),
                Metric("cpu_core_util_0", 2.544477089431855, levels=(1.0, 5.0)),
                Result(state=State.WARN, summary="Core cpu1: 2.16% (warn/crit at 1.00%/5.00%)"),
                Metric("cpu_core_util_1", 2.158715165178048, levels=(1.0, 5.0)),
            ],
        ),
        (
            {"levels_single": (80, 90), "core_util_time": (1, 1, 2)},
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
            ],
        ),
        (
            {"levels_single": (1, 5), "core_util_time": (1, 1, 2)},
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.WARN, summary="Core cpu0: 2.54% (warn/crit at 1.00%/5.00%)"),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.WARN, summary="Core cpu1: 2.16% (warn/crit at 1.00%/5.00%)"),
            ],
        ),
        (
            {"levels_single": (80, 90), "core_util_graph": True, "core_util_time": (1, 1, 2)},
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855, levels=(80.0, 90.0)),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048, levels=(80.0, 90.0)),
            ],
        ),
        (
            {"levels_single": (1, 5), "core_util_graph": True, "core_util_time": (1, 1, 2)},
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.WARN, summary="Core cpu0: 2.54% (warn/crit at 1.00%/5.00%)"),
                Metric("cpu_core_util_0", 2.544477089431855, levels=(1.0, 5.0)),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.WARN, summary="Core cpu1: 2.16% (warn/crit at 1.00%/5.00%)"),
                Metric("cpu_core_util_1", 2.158715165178048, levels=(1.0, 5.0)),
            ],
        ),
        (
            {"average_single": {"time_average": 2, "apply_levels": False, "show_graph": False}},
            CORE_RESULT,
        ),
        (
            {
                "levels_single": (80, 90),
                "average_single": {"time_average": 2, "apply_levels": False, "show_graph": False},
            },
            CORE_RESULT,
        ),
        (
            {
                "levels_single": (1, 5),
                "average_single": {"time_average": 2, "apply_levels": False, "show_graph": False},
            },
            [
                Result(state=State.WARN, summary="Core cpu0: 2.54% (warn/crit at 1.00%/5.00%)"),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Result(state=State.WARN, summary="Core cpu1: 2.16% (warn/crit at 1.00%/5.00%)"),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
            ],
        ),
        (
            {
                "levels_single": (80, 90),
                "average_single": {"time_average": 2, "apply_levels": True, "show_graph": False},
            },
            CORE_RESULT,
        ),
        (
            {
                "levels_single": (1, 5),
                "average_single": {"time_average": 2, "apply_levels": True, "show_graph": False},
            },
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(
                    state=State.WARN,
                    notice="Core cpu0 (2-min average): 2.54% (warn/crit at 1.00%/5.00%)",
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Result(
                    state=State.WARN,
                    notice="Core cpu1 (2-min average): 2.16% (warn/crit at 1.00%/5.00%)",
                ),
            ],
        ),
        (
            {
                "levels_single": (0, 1),
                "average_single": {"time_average": 2, "apply_levels": True, "show_graph": False},
            },
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(
                    state=State.CRIT,
                    summary="Core cpu0 (2-min average): 2.54% (warn/crit at 0%/1.00%)",
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Result(
                    state=State.CRIT,
                    summary="Core cpu1 (2-min average): 2.16% (warn/crit at 0%/1.00%)",
                ),
            ],
        ),
        (
            {"average_single": {"time_average": 2, "apply_levels": False, "show_graph": True}},
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Metric("cpu_core_util_average_0", 2.544477089431855),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
                Metric("cpu_core_util_average_1", 2.158715165178048),
            ],
        ),
        (
            {
                "core_util_graph": True,
                "average_single": {"time_average": 2, "apply_levels": False, "show_graph": False},
            },
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
            ],
        ),
        (
            {  # 19
                "core_util_graph": True,
                "average_single": {"time_average": 2, "apply_levels": False, "show_graph": True},
            },
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Metric("cpu_core_util_average_0", 2.544477089431855),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
                Metric("cpu_core_util_average_1", 2.158715165178048),
            ],
        ),
        (
            {  # 20
                "levels_single": (1, 5),
                "core_util_graph": True,
                "average_single": {"time_average": 2, "apply_levels": False, "show_graph": True},
            },
            [
                Result(state=State.WARN, summary="Core cpu0: 2.54% (warn/crit at 1.00%/5.00%)"),
                Metric("cpu_core_util_0", 2.544477089431855, levels=(1.0, 5.0)),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Metric("cpu_core_util_average_0", 2.544477089431855),
                Result(state=State.WARN, summary="Core cpu1: 2.16% (warn/crit at 1.00%/5.00%)"),
                Metric("cpu_core_util_1", 2.158715165178048, levels=(1.0, 5.0)),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
                Metric("cpu_core_util_average_1", 2.158715165178048),
            ],
        ),
        (
            {  # 21
                "levels_single": (0, 1),
                "core_util_graph": True,
                "average_single": {"time_average": 2, "apply_levels": False, "show_graph": True},
            },
            [
                Result(state=State.CRIT, summary="Core cpu0: 2.54% (warn/crit at 0%/1.00%)"),
                Metric("cpu_core_util_0", 2.544477089431855, levels=(0.0, 1.0)),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Metric("cpu_core_util_average_0", 2.544477089431855),
                Result(state=State.CRIT, summary="Core cpu1: 2.16% (warn/crit at 0%/1.00%)"),
                Metric("cpu_core_util_1", 2.158715165178048, levels=(0.0, 1.0)),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
                Metric("cpu_core_util_average_1", 2.158715165178048),
            ],
        ),
        (
            {  # 22
                "levels_single": (0, 1),
                "core_util_graph": True,
                "average_single": {
                    "time_average": 2,
                    "apply_levels": True,
                    "show_graph": True,
                },
            },
            [
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855),
                Result(
                    state=State.CRIT,
                    summary="Core cpu0 (2-min average): 2.54% (warn/crit at 0%/1.00%)",
                ),
                Metric("cpu_core_util_average_0", 2.544477089431855, levels=(0.0, 1.0)),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048),
                Result(
                    state=State.CRIT,
                    summary="Core cpu1 (2-min average): 2.16% (warn/crit at 0%/1.00%)",
                ),
                Metric("cpu_core_util_average_1", 2.158715165178048, levels=(0.0, 1.0)),
            ],
        ),
        (
            {  # 23
                "core_util_time": (1, 1, 2),
                "average_single": {
                    "time_average": 2,
                    "apply_levels": False,
                    "show_graph": False,
                },
            },
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds "
                        "(warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Result(state=State.OK, notice="Core cpu0 (2-min average): 2.54%"),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Result(state=State.OK, notice="Core cpu1 (2-min average): 2.16%"),
            ],
        ),
        (
            {
                "core_util_time": (1, 1, 2),
                "levels_single": (0, 1),
                "core_util_graph": True,
                "average_single": {
                    "time_average": 2,
                    "apply_levels": True,
                    "show_graph": True,
                },
            },
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu0 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu0: 2.54%"),
                Metric("cpu_core_util_0", 2.544477089431855),
                Result(
                    state=State.CRIT,
                    summary="Core cpu0 (2-min average): 2.54% (warn/crit at 0%/1.00%)",
                ),
                Metric("cpu_core_util_average_0", 2.544477089431855, levels=(0.0, 1.0)),
                Result(
                    state=State.CRIT,
                    summary=(
                        "cpu1 is under high load for: 2 minutes 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Result(state=State.OK, notice="Core cpu1: 2.16%"),
                Metric("cpu_core_util_1", 2.158715165178048),
                Result(
                    state=State.CRIT,
                    summary="Core cpu1 (2-min average): 2.16% (warn/crit at 0%/1.00%)",
                ),
                Metric("cpu_core_util_average_1", 2.158715165178048, levels=(0.0, 1.0)),
            ],
        ),
    ],
)
def test_check(monkeypatch, parameters, additional_results) -> None:
    monkeypatch.setattr(
        kernel,
        "get_value_store",
        lambda: {"cpu.util.core.high": {"cpu0": 1591285080, "cpu1": 1591285080}},
    )
    with freezegun.freeze_time("2020-06-04 15:40:00"):
        results = list(kernel.check_kernel_util(parameters, SECTION))

    assert results[: len(BASIC_RESULT)] == BASIC_RESULT
    assert results[len(BASIC_RESULT) :] == additional_results
