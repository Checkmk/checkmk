#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.viprinet.agent_based.viprinet_serial import (
    check_viprinet_serial,
    discover_viprinet_serial,
    parse_viprinet_serial,
)

_STRING_TABLE = [["A1B2C3D4"]]


def test_discover_viprinet_serial() -> None:
    section = parse_viprinet_serial(_STRING_TABLE)
    assert list(discover_viprinet_serial(section)) == [Service()]


def test_discover_viprinet_serial_no_data() -> None:
    section = parse_viprinet_serial([])
    assert list(discover_viprinet_serial(section)) == []


def test_check_viprinet_serial() -> None:
    section = parse_viprinet_serial(_STRING_TABLE)
    assert list(check_viprinet_serial(section)) == [
        Result(state=State.OK, summary="A1B2C3D4"),
    ]
