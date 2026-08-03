#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.viprinet.agent_based.viprinet_serial import (
    check_viprinet_serial,
    discover_viprinet_serial,
    parse_viprinet_serial,
)

_STRING_TABLE = [["A1B2C3D4"]]


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([], id="empty payload"),
        pytest.param([[]], id="empty nested payload"),
    ],
)
def test_parse_viprinet_serial_empty_values(string_table: StringTable) -> None:
    assert parse_viprinet_serial(string_table) is None


def test_discover_viprinet_serial() -> None:
    section = parse_viprinet_serial(_STRING_TABLE)
    assert section is not None
    assert list(discover_viprinet_serial(section)) == [Service()]


def test_check_viprinet_serial() -> None:
    section = parse_viprinet_serial(_STRING_TABLE)
    assert section is not None
    assert list(check_viprinet_serial(section)) == [
        Result(state=State.OK, summary="A1B2C3D4"),
    ]
