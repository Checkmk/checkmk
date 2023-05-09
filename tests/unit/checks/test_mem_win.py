#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest
from pytest_mock import MockerFixture

from testlib import Check

pytestmark = pytest.mark.checks

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
                (
                    1,
                    "RAM: 81.51% - 104.33 GB of 128.00 GB (warn/crit at 80.00%/90.00% used)",
                    [
                        (
                            "mem_used",
                            112020467712,
                            109950677811.20001,
                            123694512537.6,
                            0,
                            137438347264,
                        ),
                        (
                            "mem_used_percent",
                            81.50597700132717,
                            80.00000000000001,
                            90.00000000000001,
                            0.0,
                            None,
                        ),
                        ("mem_total", 131071.421875),
                    ],
                ),
                (
                    1,
                    "Commit charge: 75.43% - 110.88 GB of 147.00 GB (warn/crit at 70.00%/90.00% "
                    "used)",
                    [
                        (
                            "pagefile_used",
                            119057674240,
                            110487609344.0,
                            142055497728.0,
                            0,
                            157839441920,
                        ),
                        ("pagefile_total", 150527.421875),
                    ],
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
                (
                    0,
                    "RAM: 81.51% - 104.33 GB of 128.00 GB, 10 min average: 81.51% (104.33 GB)",
                    [
                        ("mem_used", 112020467712, None, None, 0, 137438347264),
                        ("mem_used_percent", 81.50597700132717, None, None, 0.0, None),
                        ("mem_total", 131071.421875),
                        (
                            "memory_avg",
                            106831.04296875,
                            129071.421875,
                            130071.421875,
                            0.0,
                            131071.421875,
                        ),
                    ],
                ),
                (
                    1,
                    "Commit charge: 75.43% - 110.88 GB of 147.00 GB, 10 min average: 75.43% "
                    "(110.88 GB)",
                    [
                        ("pagefile_used", 119057674240, None, None, 0, 157839441920),
                        ("pagefile_total", 150527.421875),
                        (
                            "pagefile_avg",
                            113542.24609375,
                            100527.421875,
                            146527.421875,
                            0.0,
                            150527.421875,
                        ),
                    ],
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
                (
                    1,
                    "RAM: 81.51% - 104.33 GB of 128.00 GB, RAM: 104.33 GB (predicted reference: "
                    "97.66) (warn/crit at 87.89 GB/107.42 GB)",
                    [
                        ("mem_used", 112020467712, None, None, 0, 137438347264),
                        ("mem_used_percent", 81.50597700132717, None, None, 0.0, None),
                        ("mem_total", 131071.421875),
                        ("memory", 106831.04296875, 90000, 110000),
                        ("predict_memory", 100000),
                    ],
                ),
                (
                    2,
                    "Commit charge: 75.43% - 110.88 GB of 147.00 GB, Commit charge: 110.88 GB "
                    "(predicted reference: 97.66) (warn/crit at 87.89 GB/107.42 GB)",
                    [
                        ("pagefile_used", 119057674240, None, None, 0, 157839441920),
                        ("pagefile_total", 150527.421875),
                        ("pagefile", 113542.24609375, 90000, 110000),
                        ("predict_pagefile", 100000),
                    ],
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
                (
                    1,
                    "RAM: 81.51% - 104.33 GB of 128.00 GB, 60 min average: 81.51% (104.33 GB), "
                    "RAM: 104.33 GB (predicted reference: 97.66) (warn/crit at 87.89 GB/107.42 "
                    "GB)",
                    [
                        ("mem_used", 112020467712, None, None, 0, 137438347264),
                        ("mem_used_percent", 81.50597700132717, None, None, 0.0, None),
                        ("mem_total", 131071.421875),
                        ("memory_avg", 106831.04296875, 90000, 110000),
                        ("predict_memory_avg", 100000),
                    ],
                ),
                (
                    2,
                    "Commit charge: 75.43% - 110.88 GB of 147.00 GB, 60 min average: 75.43% "
                    "(110.88 GB), Commit charge: 110.88 GB (predicted reference: 97.66) "
                    "(warn/crit at 87.89 GB/107.42 GB)",
                    [
                        ("pagefile_used", 119057674240, None, None, 0, 157839441920),
                        ("pagefile_total", 150527.421875),
                        ("pagefile_avg", 113542.24609375, 90000, 110000),
                        ("predict_pagefile_avg", 100000),
                    ],
                ),
            ],
            id="predictive levels + averaging",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_mem_win(
    mocker: MockerFixture,
    params: Mapping[str, Any],
    expected_result,
) -> None:
    mocker.patch(
        "cmk.base.check_api_utils.host_name",
        return_value="unittest-hn",
    )
    mocker.patch(
        "cmk.base.check_api_utils.service_description",
        return_value="unittest-sd",
    )
    mocker.patch(
        "cmk.base.check_api._prediction.get_levels",
        return_value=(100000, (90000, 110000, None, None)),
    )
    assert list(Check("mem.win").run_check(
        None,
        params,
        _SECTION,
    )) == expected_result
