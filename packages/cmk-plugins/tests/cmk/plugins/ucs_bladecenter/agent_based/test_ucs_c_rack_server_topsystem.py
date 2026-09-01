#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based.ucs_c_rack_server_topsystem import (
    check_ucs_c_rack_server_topsystem,
    discover_ucs_c_rack_server_topsystem,
    parse_ucs_c_rack_server_topsystem,
)

_SECTION = parse_ucs_c_rack_server_topsystem(
    [
        [
            "topSystem",
            "dn sys",
            "address 192.168.1.1",
            "currentTime Wed Feb  6 09:12:12 2019",
            "mode stand-alone",
            "name CIMC-istreamer2a-etn",
        ]
    ]
)


def test_discover_ucs_c_rack_server_topsystem() -> None:
    assert list(discover_ucs_c_rack_server_topsystem(_SECTION)) == [Service()]


def test_discover_ucs_c_rack_server_topsystem_without_data() -> None:
    assert not list(discover_ucs_c_rack_server_topsystem(parse_ucs_c_rack_server_topsystem([])))


def test_check_ucs_c_rack_server_topsystem() -> None:
    assert list(check_ucs_c_rack_server_topsystem(_SECTION)) == [
        Result(state=State.OK, summary="DN: sys"),
        Result(state=State.OK, summary="IP: 192.168.1.1"),
        Result(state=State.OK, summary="Mode: stand-alone"),
        Result(state=State.OK, summary="Name: CIMC-istreamer2a-etn"),
        Result(state=State.OK, summary="Date and time: 2019-02-06 09:12:12"),
    ]


def test_check_ucs_c_rack_server_topsystem_unparsable_time() -> None:
    section = parse_ucs_c_rack_server_topsystem(
        [
            [
                "topSystem",
                "dn sys",
                "address 192.168.1.1",
                "currentTime nonsense",
                "mode stand-alone",
                "name CIMC-istreamer2a-etn",
            ]
        ]
    )
    assert list(check_ucs_c_rack_server_topsystem(section))[-1] == Result(
        state=State.OK, summary="Date and time: unknown[entTime nonsense]"
    )
