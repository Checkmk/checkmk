#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest
from pytest_mock import MockerFixture

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugin_contexts import current_host, current_service
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

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


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "memory": (80.0, 90.0),
                "pagefile": (70.0, 90.0),
            },
            [
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104.33 GB of 128.00 GB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric(
                    "mem_used",
                    112020467712.0,
                    levels=(109950677811.20001, 123694512537.6),
                    boundaries=(0.0, 137438347264.0),
                ),
                Metric(
                    "mem_used_percent",
                    81.50597700132717,
                    levels=(80.00000000000001, 90.00000000000001),
                    boundaries=(0.0, None),
                ),
                Metric(
                    "mem_total",
                    131071.421875,
                ),
                Result(
                    state=State.WARN,
                    summary="Commit charge: 75.43% - 110.88 GB of 147.00 GB (warn/crit at 70.00%/90.00% used)",
                ),
                Metric(
                    "pagefile_used",
                    119057674240.0,
                    levels=(110487609344.0, 142055497728.0),
                    boundaries=(0.0, 157839441920.0),
                ),
                Metric(
                    "pagefile_total",
                    150527.421875,
                ),
            ],
            id="normal levels",
        ),
        pytest.param(
            {
                "memory": (2000, 1000),
                "pagefile": (50000, 4000),
                "average": 10,
            },
            [
                Result(
                    state=State.OK,
                    summary="RAM: 81.51% - 104.33 GB of 128.00 GB, 10 min average: 81.51% (104.33 GB)",
                ),
                Metric(
                    "mem_used",
                    112020467712.0,
                    boundaries=(0.0, 137438347264.0),
                ),
                Metric(
                    "mem_used_percent",
                    81.50597700132717,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "mem_total",
                    131071.421875,
                ),
                Metric(
                    "memory_avg",
                    106831.04296875,
                    levels=(129071.421875, 130071.421875),
                    boundaries=(0.0, 131071.421875),
                ),
                Result(
                    state=State.WARN,
                    summary="Commit charge: 75.43% - 110.88 GB of 147.00 GB, 10 min average: 75.43% (110.88 GB)",
                ),
                Metric(
                    "pagefile_used",
                    119057674240.0,
                    boundaries=(0.0, 157839441920.0),
                ),
                Metric(
                    "pagefile_total",
                    150527.421875,
                ),
                Metric(
                    "pagefile_avg",
                    113542.24609375,
                    levels=(100527.421875, 146527.421875),
                    boundaries=(0.0, 150527.421875),
                ),
            ],
            id="normal levels + averaging",
        ),
        pytest.param(
            {
                "memory": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                },
                "pagefile": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                },
            },
            [
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104.33 GB of 128.00 GB, RAM: 104.33 GB (predicted reference: 97.66) (warn/crit at 87.89 GB/107.42 GB)",
                ),
                Metric(
                    "mem_used",
                    112020467712.0,
                    boundaries=(0.0, 137438347264.0),
                ),
                Metric(
                    "mem_used_percent",
                    81.50597700132717,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "mem_total",
                    131071.421875,
                ),
                Metric(
                    "memory",
                    106831.04296875,
                    levels=(90000.0, 110000.0),
                ),
                Metric(
                    "predict_memory",
                    100000.0,
                ),
                Result(
                    state=State.CRIT,
                    summary="Commit charge: 75.43% - 110.88 GB of 147.00 GB, Commit charge: 110.88 GB (predicted reference: 97.66) (warn/crit at 87.89 GB/107.42 GB)",
                ),
                Metric(
                    "pagefile_used",
                    119057674240.0,
                    boundaries=(0.0, 157839441920.0),
                ),
                Metric(
                    "pagefile_total",
                    150527.421875,
                ),
                Metric(
                    "pagefile",
                    113542.24609375,
                    levels=(90000.0, 110000.0),
                ),
                Metric(
                    "predict_pagefile",
                    100000.0,
                ),
            ],
            id="predictive levels",
        ),
        pytest.param(
            {
                "memory": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                },
                "pagefile": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                },
                "average": 60,
            },
            [
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104.33 GB of 128.00 GB, 60 min average: 81.51% (104.33 GB), RAM: 104.33 GB (predicted reference: 97.66) (warn/crit at 87.89 GB/107.42 GB)",
                ),
                Metric(
                    "mem_used",
                    112020467712.0,
                    boundaries=(0.0, 137438347264.0),
                ),
                Metric(
                    "mem_used_percent",
                    81.50597700132717,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "mem_total",
                    131071.421875,
                ),
                Metric(
                    "memory_avg",
                    106831.04296875,
                    levels=(90000.0, 110000.0),
                ),
                Metric(
                    "predict_memory_avg",
                    100000.0,
                ),
                Result(
                    state=State.CRIT,
                    summary="Commit charge: 75.43% - 110.88 GB of 147.00 GB, 60 min average: 75.43% (110.88 GB), Commit charge: 110.88 GB (predicted reference: 97.66) (warn/crit at 87.89 GB/107.42 GB)",
                ),
                Metric(
                    "pagefile_used",
                    119057674240.0,
                    boundaries=(0.0, 157839441920.0),
                ),
                Metric(
                    "pagefile_total",
                    150527.421875,
                ),
                Metric(
                    "pagefile_avg",
                    113542.24609375,
                    levels=(90000.0, 110000.0),
                ),
                Metric(
                    "predict_pagefile_avg",
                    100000.0,
                ),
            ],
            id="predictive levels + averaging",
        ),
    ],
)
def test_mem_win(
    mocker: MockerFixture,
    fix_register: FixRegister,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    mocker.patch(
        "cmk.base.check_api._prediction.get_levels",
        return_value=(100000, (90000, 110000, None, None)),
    )
    with current_host("unittest-hn"), current_service(
        CheckPluginName("unittest_sd"), "unittest_sd_description"
    ):
        assert (
            list(
                fix_register.check_plugins[CheckPluginName("mem_win")].check_function(
                    item=None,
                    params=params,
                    section=_SECTION,
                )
            )
            == expected_result
        )
