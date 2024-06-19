#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.alcatel_power import (
    check_alcatel_power,
    discover_alcatel_power,
    parse_alcatel_power,
)

INFO = [
    ["1", "1", "0"],
    ["2", "1", "1"],
    ["3", "1", ""],
    ["4", "1", "0"],
    ["5", "1", "1"],
    ["6", "1", ""],
    ["7", "2", "0"],
    ["8", "2", "1"],
    ["9", "2", ""],
    ["10", "2", "0"],
    ["11", "2", "1"],
    ["12", "2", ""],
]


def test_discovery_function() -> None:
    assert list(discover_alcatel_power(parse_alcatel_power(INFO))) == [
        Service(item="11"),
        Service(item="8"),
        Service(item="5"),
        Service(item="2"),
    ]


def test_check_function_up() -> None:
    assert list(check_alcatel_power("2", parse_alcatel_power(INFO))) == [
        Result(state=State.OK, summary="[AC] Operational status: up"),
    ]


def test_check_function_down() -> None:
    assert list(check_alcatel_power("11", parse_alcatel_power(INFO))) == [
        Result(state=State.CRIT, summary="[AC] Operational status: down"),
    ]
