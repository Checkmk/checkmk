#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_socomec_capacity import (
    check_ups_socomec_capacity,
    discover_ups_socomec_capacity,
    parse_ups_socomec_capacity,
)

_PARAMS = {"battime": (0, 0), "capacity": (95, 90)}


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["0", "360", "100"]], [Service()]),
        ([], []),
    ],
)
def test_discover_ups_socomec_capacity(string_table: StringTable, expected: list[Service]) -> None:
    assert list(discover_ups_socomec_capacity(parse_ups_socomec_capacity(string_table))) == expected


def test_check_ups_socomec_capacity_ok() -> None:
    assert list(check_ups_socomec_capacity(_PARAMS, [["0", "360", "100"]])) == [
        Result(state=State.OK, summary="360 min left on battery"),
        Metric("capacity", 360.0),
        Result(state=State.OK, summary="capacity: 100%"),
        Metric("percent", 100.0, levels=(95.0, 90.0)),
    ]


def test_check_ups_socomec_capacity_on_battery_low() -> None:
    assert list(check_ups_socomec_capacity(_PARAMS, [["5", "30", "50"]])) == [
        Result(state=State.OK, summary="30 min left on battery"),
        Metric("capacity", 30.0),
        Result(state=State.CRIT, summary="capacity: 50% (crit at 90%)"),
        Metric("percent", 50.0, levels=(95.0, 90.0)),
        Result(state=State.OK, summary="On battery for 5 min"),
    ]
