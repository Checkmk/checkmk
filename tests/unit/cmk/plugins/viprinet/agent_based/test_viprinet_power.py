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


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([], id="empty payload"),
        pytest.param([[]], id="empty nested payload"),
    ],
)
def test_parse_viprinet_power_empty_values(string_table: StringTable) -> None:
    assert parse_viprinet_power(string_table) is None


def test_discover_viprinet_power() -> None:
    section = parse_viprinet_power(_STRING_TABLE)
    assert section is not None
    assert list(discover_viprinet_power(section)) == [Service()]


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
    assert section is not None
    assert list(check_viprinet_power(section)) == expected
