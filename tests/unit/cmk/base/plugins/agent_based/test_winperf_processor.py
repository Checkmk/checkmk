#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import winperf_processor
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    Metric,
    Result,
    Service,
    State,
)

INFO = [
    ["1556221294.75", "238", "10000000"],
    ["5", "instances:", "0", "1", "2", "3", "_Total"],
    [
        "-232",
        "20854932656250",
        "20941215937500",
        "20895696562500",
        "20931057343750",
        "20905725625000",
        "100nsec_timer_inv",
    ],
    [
        "-96",
        "767188437500",
        "738879375000",
        "737527500000",
        "742882343750",
        "746619414062",
        "100nsec_timer",
    ],
    [
        "-94",
        "121450781250",
        "63474218750",
        "110345468750",
        "69629843750",
        "91225078125",
        "100nsec_timer",
    ],
    ["-90", "506534602", "346655884", "508018892", "352757259", "1713966637", "counter"],
    [
        "458",
        "30148750000",
        "2639375000",
        "23398281250",
        "2215468750",
        "14600468750",
        "100nsec_timer",
    ],
    ["460", "5290312500", "3367968750", "4306406250", "5563281250", "4631992187", "100nsec_timer"],
    ["1096", "173713449", "37720286", "172867460", "31918437", "416219632", "counter"],
    ["1098", "2", "0", "1", "0", "3", "rawcount"],
    [
        "1508",
        "20744654902969",
        "20848687646812",
        "20771013615262",
        "20842396380778",
        "20801688136455",
        "100nsec_timer",
    ],
    [
        "1510",
        "20744654902969",
        "20848687646812",
        "20771013615262",
        "20842396380778",
        "20801688136455",
        "100nsec_timer",
    ],
    ["1512", "0", "0", "0", "0", "0", "100nsec_timer"],
    ["1514", "0", "0", "0", "0", "0", "100nsec_timer"],
    ["1516", "393050574", "290618823", "401461357", "296238855", "1381369609", "bulk_count"],
    ["1518", "0", "0", "0", "0", "0", "bulk_count"],
    ["1520", "0", "0", "0", "0", "0", "bulk_count"],
]

SECTION = winperf_processor.Section(
    time=1556221294,
    ticks=[
        winperf_processor.CoreTicks(
            name="util",
            total=20905725625000,
            per_core=[20854932656250, 20941215937500, 20895696562500, 20931057343750],
        ),
        winperf_processor.CoreTicks(
            name="user",
            total=746619414062,
            per_core=[767188437500, 738879375000, 737527500000, 742882343750],
        ),
        winperf_processor.CoreTicks(
            name="privileged",
            total=91225078125,
            per_core=[121450781250, 63474218750, 110345468750, 69629843750],
        ),
    ],
)

VALUE_STORE = {
    "util": (1556221234.75, 20905725624000),
    "util.0": (1556221234.75, 20854932656100),
    "util.1": (1556221234.75, 20941215937000),
    "util.2": (1556221234.75, 20895696561500),
    "util.3": (1556221234.75, 20931057343740),
    "user": (1556221234.75, 746619411062),
    "privileged": (1556221234.75, 91225078025),
}


def test_parse_function():
    assert winperf_processor.parse_winperf_processor(INFO) == SECTION


def test_discovery():
    assert list(winperf_processor.discover_winperf_processor_util(SECTION)) == [
        Service(),
    ]


@pytest.mark.parametrize(
    "value_store, params, result",
    [
        (
            {},
            {},
            [
                IgnoreResults("Initialized: 'util'"),
                IgnoreResults("Initialized: 'user'"),
                IgnoreResults("Initialized: 'privileged'"),
                Result(state=State.OK, notice="Number of processors: 4"),
                Metric("cpus", 4),
            ],
        ),
        (
            VALUE_STORE,
            {},
            [
                Result(state=State.OK, summary="Total CPU: 100.00%"),
                Metric("util", 99.99983122362869, boundaries=(0, 4)),  # boundaries: 4 as in 4 CPUs
                Result(state=State.OK, notice="User: <0.01%"),
                Metric("user", 0.0005063291139240507),
                Result(state=State.OK, notice="Privileged: <0.01%"),
                Metric("privileged", 1.687763713080169e-05),
                Result(state=State.OK, notice="Number of processors: 4"),
                Metric("cpus", 4),
            ],
        ),
        (
            VALUE_STORE,
            {"levels": (90, 95)},
            [
                Result(state=State.CRIT, summary="Total CPU: 100.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 99.99983122362869, levels=(90.0, 95.0), boundaries=(0, 4)),
                Result(state=State.OK, notice="User: <0.01%"),
                Metric("user", 0.0005063291139240507),
                Result(state=State.OK, notice="Privileged: <0.01%"),
                Metric("privileged", 1.687763713080169e-05),
                Result(state=State.OK, notice="Number of processors: 4"),
                Metric("cpus", 4),
            ],
        ),
    ],
)
def test_check(monkeypatch, value_store, params, result):
    monkeypatch.setattr(winperf_processor, "get_value_store", value_store.copy)
    assert list(winperf_processor.check_winperf_processor_util(params, SECTION)) == result
