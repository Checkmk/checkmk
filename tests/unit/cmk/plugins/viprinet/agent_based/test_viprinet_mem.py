#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.viprinet.agent_based.viprinet_mem import (
    check_viprinet_mem,
    discover_viprinet_mem,
    parse_viprinet_mem,
)

_STRING_TABLE = [["1048576"]]


def test_discover_viprinet_mem() -> None:
    section = parse_viprinet_mem(_STRING_TABLE)
    assert list(discover_viprinet_mem(section)) == [Service()]


def test_discover_viprinet_mem_no_data() -> None:
    section = parse_viprinet_mem([])
    assert list(discover_viprinet_mem(section)) == []


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            [["1048576"]],
            [Result(state=State.OK, summary="Memory used: 1.00 MiB")],
        ),
        (
            [["not-a-number"]],
            [Result(state=State.OK, summary="Memory used: 0 B")],
        ),
    ],
)
def test_check_viprinet_mem(string_table: StringTable, expected: list[Result]) -> None:
    section = parse_viprinet_mem(string_table)
    assert list(check_viprinet_mem(section)) == expected
