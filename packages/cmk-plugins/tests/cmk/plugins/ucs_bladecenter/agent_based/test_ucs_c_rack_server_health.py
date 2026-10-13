#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based.ucs_c_rack_server_health import (
    check_ucs_c_rack_server_health,
    discover_ucs_c_rack_server_health,
    parse_ucs_c_rack_server_health,
)

_SECTION = parse_ucs_c_rack_server_health(
    [
        [
            "storageControllerHealth",
            "dn sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0",
            "id SLOT-HBA",
            "health Good",
        ],
        [
            "storageControllerHealth",
            "dn sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0",
            "id SLOT-HBA",
            "health Bogus",
        ],
    ]
)


def test_discover_ucs_c_rack_server_health() -> None:
    assert list(discover_ucs_c_rack_server_health(_SECTION)) == [
        Service(item="Rack unit 1 Storage SAS SLOT HBA vd 0"),
        Service(item="Rack unit 2 Storage SAS SLOT HBA vd 0"),
    ]


def test_check_ucs_c_rack_server_health() -> None:
    assert list(
        check_ucs_c_rack_server_health("Rack unit 1 Storage SAS SLOT HBA vd 0", _SECTION)
    ) == [Result(state=State.OK, summary="Status: good")]


def test_check_ucs_c_rack_server_health_undocumented_value() -> None:
    # "Good" is the only value known from exemplary data output.
    assert list(
        check_ucs_c_rack_server_health("Rack unit 2 Storage SAS SLOT HBA vd 0", _SECTION)
    ) == [Result(state=State.UNKNOWN, summary="Status: unknown[bogus]")]


def test_check_ucs_c_rack_server_health_vanished_item() -> None:
    assert not list(check_ucs_c_rack_server_health("Rack unit 3", _SECTION))
