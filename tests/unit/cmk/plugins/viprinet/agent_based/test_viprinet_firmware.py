#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.viprinet.agent_based.viprinet_firmware import (
    check_viprinet_firmware,
    discover_viprinet_firmware,
    parse_viprinet_firmware,
)

_STRING_TABLE = [["1.06", "0"]]


def test_discover_viprinet_firmware() -> None:
    section = parse_viprinet_firmware(_STRING_TABLE)
    assert list(discover_viprinet_firmware(section)) == [Service()]


def test_discover_viprinet_firmware_no_data() -> None:
    section = parse_viprinet_firmware([])
    assert list(discover_viprinet_firmware(section)) == []


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            [["1.06", "0"]],
            [Result(state=State.OK, summary="1.06, No new firmware available")],
        ),
        (
            [["1.06", "1"]],
            [Result(state=State.OK, summary="1.06, Update Available")],
        ),
        (
            [["1.06", "2"]],
            [Result(state=State.OK, summary="1.06, Checking for Updates")],
        ),
        (
            [["1.06", "3"]],
            [Result(state=State.OK, summary="1.06, Downloading Update")],
        ),
        (
            [["1.06", "4"]],
            [Result(state=State.OK, summary="1.06, Installing Update")],
        ),
        (
            [["1.06", "9"]],
            [Result(state=State.UNKNOWN, summary="1.06, No firmware status available")],
        ),
    ],
)
def test_check_viprinet_firmware(string_table: StringTable, expected: list[Result]) -> None:
    section = parse_viprinet_firmware(string_table)
    assert list(check_viprinet_firmware(section)) == expected
