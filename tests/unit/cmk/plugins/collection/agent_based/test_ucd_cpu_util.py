#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import ucd_cpu_util as ucu

FREEZE_TIME = "1970-01-01 00:01:00Z"

STRING_TABLE = [
    [
        "systemStats",
        "592290145",
        "25568640",
        "380156988",
        "1565290934",
        "42658",
        "0",
        "1929381994",
        "1861656198",
        "349584702",
    ]
]


def _section() -> ucu.Section:
    assert (section := ucu.parse_ucd_cpu_util(STRING_TABLE)) is not None
    return section


def test_discovery() -> None:
    assert list(ucu.inventory_ucd_cpu_util(_section())) == [Service()]


def test_check() -> None:
    assert list(
        ucu.check_ucd_cpu_util_with_context(
            {}, _section(), 60.0, {"io_received": (0, 0), "io_send": (0, 0)}
        )
    ) == [
        Result(state=State.OK, notice="User: 21.21%"),
        Metric("user", 21.210874355159238),
        Result(state=State.OK, notice="System: 25.05%"),
        Metric("system", 25.051775056191136),
        Result(state=State.OK, notice="Wait: <0.01%"),
        Metric("wait", 0.001464434107289391),
        Result(state=State.OK, summary="Total CPU: 46.26%"),
        Metric("util", 46.264113845457665, boundaries=(0.0, None)),
        Metric("read_blocks", 31027603.3),
        Metric("write_blocks", 32156366.566666666),
    ]
