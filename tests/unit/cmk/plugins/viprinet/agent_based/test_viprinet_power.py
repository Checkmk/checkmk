#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.viprinet.agent_based.viprinet_power import (
    check_viprinet_power,
    discover_viprinet_power,
    parse_viprinet_power,
)

_STRING_TABLE = [["0"]]


def test_discover_viprinet_power() -> None:
    section = parse_viprinet_power(_STRING_TABLE)
    assert list(discover_viprinet_power(section)) == [Service()]


def test_discover_viprinet_power_no_data() -> None:
    section = parse_viprinet_power([])
    assert list(discover_viprinet_power(section)) == []


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            [["0"]],
            [Result(state=State.OK, summary="no failure")],
        ),
        (
            [["1"]],
            [Result(state=State.OK, summary="a single PSU is out of order")],
        ),
        (
            [["9"]],
            [Result(state=State.UNKNOWN, summary="Invalid power status")],
        ),
    ],
)
def test_check_viprinet_power(string_table: StringTable, expected: list[Result]) -> None:
    section = parse_viprinet_power(string_table)
    assert list(check_viprinet_power(section)) == expected
