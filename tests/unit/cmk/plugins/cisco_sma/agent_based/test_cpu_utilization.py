#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.cisco_sma.agent_based.cpu_utilization import (
    _check_cpu_utilization_testable,
    _discover_cpu_utilization,
    _parse_cpu_utilization,
)


def test_parse_cpu_utilizations() -> None:
    assert _parse_cpu_utilization([["10"]]) == 10.0
    assert _parse_cpu_utilization([]) is None


def test_discover_cpu_utilization() -> None:
    assert list(_discover_cpu_utilization(21.0)) == [Service()]


def test_check_cpu_utilization_testable() -> None:
    assert list(
        _check_cpu_utilization_testable(util=21.0, params={}, value_store={}, this_time=0.0)
    ) == [
        Result(state=State.OK, summary="Total CPU: 21.00%"),
        Metric("util", 21.0, boundaries=(0.0, None)),
    ]
