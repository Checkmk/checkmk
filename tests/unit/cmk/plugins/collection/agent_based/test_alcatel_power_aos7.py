#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.alcatel_power_aos7 import (
    check_alcatel_power_aos7,
    discover_alcatel_power_aos7,
    parse_alcatel_power_aos7,
)

INFO = [
    ["1", "1", "1"],
    ["2", "2", "1"],
    ["3", "3", "1"],
    ["4", "4", "1"],
    ["5", "5", "0"],
    ["6", "6", "0"],
    ["7", "7", "0"],
    ["8", "8", "2"],
    ["9", "9", "2"],
    ["10", "10", "2"],
]


def test_discovery_function() -> None:
    assert list(discover_alcatel_power_aos7(parse_alcatel_power_aos7(INFO))) == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
        Service(item="4"),
        Service(item="8"),
        Service(item="9"),
        Service(item="10"),
    ]


def test_check_function_up() -> None:
    assert list(check_alcatel_power_aos7("1", parse_alcatel_power_aos7(INFO))) == [
        Result(state=State.OK, summary="[AC] Status: up")
    ]


def test_check_function_power_save() -> None:
    assert list(check_alcatel_power_aos7("10", parse_alcatel_power_aos7(INFO))) == [
        Result(state=State.CRIT, summary="[DC] Status: power save")
    ]


def test_check_function_down() -> None:
    assert list(check_alcatel_power_aos7("2", parse_alcatel_power_aos7(INFO))) == [
        Result(state=State.CRIT, summary="[AC] Status: down")
    ]
