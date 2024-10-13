#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.memory.agent_based.mem_win import check_mem_windows_static, Params

_SECTION = {
    "MemTotal": 137438347264,
    "MemFree": 25417879552,
    "SwapTotal": 20401094656,
    "SwapFree": 13363888128,
    "PageTotal": 157839441920,
    "PageFree": 38781767680,
    "VirtualTotal": 140737488224256,
    "VirtualFree": 140737374928896,
}


PREDICTED_VALUE_MEM = 104857600000.0

PREDICTED_VALUE_PGF = 100000000000.0


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            Params(
                memory={
                    "perc_used": {
                        "lower": ("no_levels", None),
                        "upper": ("fixed", (80.0, 90.0)),
                    },
                },
                pagefile={
                    "perc_used": {
                        "lower": ("no_levels", None),
                        "upper": ("fixed", (70.0, 90.0)),
                    },
                },
            ),
            [
                Result(
                    state=State.OK,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB",
                ),
                Result(state=State.WARN, summary="Used: 81.51% (warn/crit at 80.00%/90.00%)"),
                Metric("mem_used_percent", 81.50597700132717, levels=(80.0, 90.0)),
                Result(state=State.OK, notice="Used: 104 GiB"),
                Metric("mem_used", 112020467712.0),
                Result(state=State.OK, notice="Free: 23.7 GiB"),
                Metric("mem_free", 25417879552.0),
                Result(state=State.OK, summary="Virtual memory: 75.43% - 111 GiB of 147 GiB"),
                Result(state=State.WARN, summary="Used: 75.43% (warn/crit at 70.00%/90.00%)"),
                Metric("pagefile_used_percent", 75.4296092229873, levels=(70.0, 90.0)),
                Result(state=State.OK, notice="Used: 111 GiB"),
                Metric("pagefile_used", 119057674240.0),
                Result(state=State.OK, notice="Free: 36.1 GiB"),
                Metric("pagefile_free", 38781767680.0),
            ],
            id="normal levels",
        ),
        pytest.param(
            Params(
                memory={
                    "abs_free": {
                        "lower": ("fixed", (2097152000, 1048576000)),
                        "upper": ("no_levels", None),
                    },
                },
                pagefile={
                    "abs_free": {
                        "lower": ("fixed", (52428800000, 4194304000)),
                        "upper": ("no_levels", None),
                    },
                },
                average=600.0,
            ),
            [
                Result(
                    state=State.OK,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB",
                ),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, 100.0)),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_free", 25417879552.0, boundaries=(0.0, 137438347264.0)),
                Result(state=State.OK, notice="Used (averaged over 10 minutes 0 seconds): 81.51%"),
                Metric("mem_used_percent_avg", 81.50597700132717),
                Result(state=State.OK, notice="Used (averaged over 10 minutes 0 seconds): 104 GiB"),
                Metric("mem_used_avg", 112020467712.0),
                Result(
                    state=State.OK, notice="Free (averaged over 10 minutes 0 seconds): 23.7 GiB"
                ),
                Metric("mem_free_avg", 25417879552.0),
                Result(state=State.OK, summary="Virtual memory: 75.43% - 111 GiB of 147 GiB"),
                Metric("pagefile_used_percent", 75.4296092229873, boundaries=(0.0, 100.0)),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("pagefile_free", 38781767680.0, boundaries=(0.0, 157839441920.0)),
                Result(state=State.OK, notice="Used (averaged over 10 minutes 0 seconds): 75.43%"),
                Metric("pagefile_used_percent_avg", 75.4296092229873),
                Result(state=State.OK, notice="Used (averaged over 10 minutes 0 seconds): 111 GiB"),
                Metric("pagefile_used_avg", 119057674240.0),
                Result(
                    state=State.WARN,
                    summary="Free (averaged over 10 minutes 0 seconds): 36.1 GiB (warn/crit below 48.8 GiB/3.91 GiB)",
                ),
                Metric("pagefile_free_avg", 38781767680.0),
            ],
            id="normal levels + averaging",
        ),
        pytest.param(
            Params(
                memory={
                    "abs_used": {
                        "upper": (
                            "predictive",
                            (
                                "mem_used",
                                PREDICTED_VALUE_MEM,
                                (int(PREDICTED_VALUE_MEM * 0.9), int(PREDICTED_VALUE_MEM * 1.1)),
                            ),
                        ),
                        "lower": ("no_levels", None),
                    },
                },
                pagefile={
                    "abs_used": {
                        "upper": (
                            "predictive",
                            (
                                "pagefile_used",
                                PREDICTED_VALUE_PGF,
                                (int(PREDICTED_VALUE_PGF * 0.9), int(PREDICTED_VALUE_PGF * 1.1)),
                            ),
                        ),
                        "lower": ("no_levels", None),
                    }
                },
            ),
            [
                Result(state=State.OK, summary="RAM: 81.51% - 104 GiB of 128 GiB"),
                Result(state=State.OK, notice="Used: 81.51%"),
                Metric("mem_used_percent", 81.50597700132717),
                Result(
                    state=State.WARN,
                    summary="Used: 104 GiB (prediction: 97.7 GiB) (warn/crit at 87.9 GiB/107 GiB)",
                ),
                Metric("mem_used", 112020467712.0, levels=(94371840000.0, 115343360000.0)),
                Metric("predict_mem_used", 104857600000.0),
                Result(state=State.OK, notice="Free: 23.7 GiB"),
                Metric("mem_free", 25417879552.0),
                Result(state=State.OK, summary="Virtual memory: 75.43% - 111 GiB of 147 GiB"),
                Result(state=State.OK, notice="Used: 75.43%"),
                Metric("pagefile_used_percent", 75.4296092229873),
                Result(
                    state=State.CRIT,
                    summary="Used: 111 GiB (prediction: 93.1 GiB) (warn/crit at 83.8 GiB/102 GiB)",
                ),
                Metric("pagefile_used", 119057674240.0, levels=(90000000000.0, 110000000000.0)),
                Metric("predict_pagefile_used", 100000000000.0),
                Result(state=State.OK, notice="Free: 36.1 GiB"),
                Metric("pagefile_free", 38781767680.0),
            ],
            id="predictive levels",
        ),
        pytest.param(
            Params(
                memory={
                    "abs_used": {
                        "lower": ("no_levels", None),
                        "upper": (
                            "predictive",
                            (
                                "mem_used",
                                PREDICTED_VALUE_MEM,
                                (int(PREDICTED_VALUE_MEM * 0.9), int(PREDICTED_VALUE_MEM * 1.1)),
                            ),
                        ),
                    },
                },
                pagefile={
                    "abs_used": {
                        "lower": ("no_levels", None),
                        "upper": (
                            "predictive",
                            (
                                "pagefile_used",
                                PREDICTED_VALUE_PGF,
                                (int(PREDICTED_VALUE_PGF * 0.9), int(PREDICTED_VALUE_PGF * 1.1)),
                            ),
                        ),
                    },
                },
                average=3600.0,
            ),
            [
                Result(state=State.OK, summary="RAM: 81.51% - 104 GiB of 128 GiB"),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, 100.0)),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_free", 25417879552.0, boundaries=(0.0, 137438347264.0)),
                Result(state=State.OK, notice="Used (averaged over 1 hour 0 minutes): 81.51%"),
                Metric("mem_used_percent_avg", 81.50597700132717),
                Result(
                    state=State.WARN,
                    summary="Used (averaged over 1 hour 0 minutes): 104 GiB (prediction: 97.7 GiB) (warn/crit at 87.9 GiB/107 GiB)",
                ),
                Metric("mem_used_avg", 112020467712.0, levels=(94371840000.0, 115343360000.0)),
                Metric("predict_mem_used", 104857600000.0),
                Result(state=State.OK, notice="Free (averaged over 1 hour 0 minutes): 23.7 GiB"),
                Metric("mem_free_avg", 25417879552.0),
                Result(state=State.OK, summary="Virtual memory: 75.43% - 111 GiB of 147 GiB"),
                Metric("pagefile_used_percent", 75.4296092229873, boundaries=(0.0, 100.0)),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("pagefile_free", 38781767680.0, boundaries=(0.0, 157839441920.0)),
                Result(state=State.OK, notice="Used (averaged over 1 hour 0 minutes): 75.43%"),
                Metric("pagefile_used_percent_avg", 75.4296092229873),
                Result(
                    state=State.CRIT,
                    summary="Used (averaged over 1 hour 0 minutes): 111 GiB (prediction: 93.1 GiB) (warn/crit at 83.8 GiB/102 GiB)",
                ),
                Metric("pagefile_used_avg", 119057674240.0, levels=(90000000000.0, 110000000000.0)),
                Metric("predict_pagefile_used", 100000000000.0),
                Result(state=State.OK, notice="Free (averaged over 1 hour 0 minutes): 36.1 GiB"),
                Metric("pagefile_free_avg", 38781767680.0),
            ],
            id="predictive levels + averaging",
        ),
    ],
)
def test_mem_win(
    params: Params,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_mem_windows_static(
                params=params,
                section=_SECTION,
                value_store={},
                now=time.time(),
            )
        )
        == expected_result
    )
