#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import winperf_msx_queues
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

ZERO_INSTANCES_INFO = [
    ["12947176002.19"],
    ["0", "instances:", "_total"],
    ["10334", "0", "rawcount"],
    ["10336", "810", "rawcount"],
    ["10338", "0", "rawcount"],
]

INFO = [
    ["12947176002.19"],
    ["1", "instances:", "_total"],
    ["10334", "0", "rawcount"],
    ["10336", "810", "rawcount"],
    ["10338", "0", "rawcount"],
]

SECTION: winperf_msx_queues.ParsedSection = {
    10334: 0,
    10336: 810,
    10338: 0,
}

EXCHANGE_2013_SERVER_INFO = [
    ["1385554029.05", "12048"],
    ["4", "instances:", "niedrige_priorität", "normale_priorität", "hohe_priorität", "total"],
    ["2", "0", "0", "0", "2100", "rawcount"],
    ["4", "0", "0", "0", "0", "rawcount"],
    ["6", "0", "0", "0", "0", "rawcount"],
    ["8", "0", "0", "0", "0", "rawcount"],  # will be ignored
    ["44", "0", "0", "0", "42", "rawcount"],
]

EXCHANGE_2013_SERVER_SECTION: winperf_msx_queues.ParsedSection = {
    2: 2100,
    4: 0,
    6: 0,
    8: 0,
    44: 42,
}


@pytest.mark.parametrize(
    "info, section",
    [
        (ZERO_INSTANCES_INFO, {}),
        (INFO, SECTION),
        (EXCHANGE_2013_SERVER_INFO, EXCHANGE_2013_SERVER_SECTION),
    ],
)
def test_parse_function(info, section):
    assert winperf_msx_queues.parse_winperf_msx_queues(info) == section


@pytest.mark.parametrize(
    "section, services",
    [
        (SECTION, []),
        (
            EXCHANGE_2013_SERVER_SECTION,
            [
                Service(item=queue[0], parameters={"offset": queue[1]})
                for queue in winperf_msx_queues._DEFAULT_DISCOVERY_PARAMETERS["queue_names"]
            ],
        ),
    ],
)
def test_discovery(section, services):
    assert (
        list(
            winperf_msx_queues.discover_winperf_msx_queues(
                winperf_msx_queues._DEFAULT_DISCOVERY_PARAMETERS, section
            )
        )
        == services
    )


@pytest.mark.parametrize(
    "item, params, result",
    [
        (
            "Active Remote Delivery",
            {
                "levels": winperf_msx_queues._DEFAULT_LEVELS,
                "offset": 2,
            },
            [
                Result(state=State.CRIT, summary="Length: 2100 (warn/crit at 500/2000)"),
                Metric("length", 2100.0, levels=winperf_msx_queues._DEFAULT_LEVELS),
            ],
        ),
        (
            "Retry Remote Delivery",
            {
                "levels": winperf_msx_queues._DEFAULT_LEVELS,
                "offset": 4,
            },
            [
                Result(state=State.OK, summary="Length: 0"),
                Metric("length", 0.0, levels=winperf_msx_queues._DEFAULT_LEVELS),
            ],
        ),
    ],
)
def test_check(item, params, result):
    assert (
        list(
            winperf_msx_queues.check_winperf_msx_queues(item, params, EXCHANGE_2013_SERVER_SECTION)
        )
        == result
    )
