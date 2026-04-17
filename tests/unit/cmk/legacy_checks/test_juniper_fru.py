#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.legacy_checks.juniper_fru import check_juniper_fru
from cmk.plugins.juniper.agent_based.juniper_fru_section import parse_juniper_fru

_SECTION = {
    "Power Supply 0": {"fru_type": "7", "fru_state": "6"},
    "Power Supply 1": {"fru_type": "7", "fru_state": "3"},
    "Fan Tray 0 Fan 0": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 0 Fan 1": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 1 Fan 0": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 1 Fan 1": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 2 Fan 0": {"fru_type": "13", "fru_state": "6"},
    "Fan Tray 2 Fan 1": {"fru_type": "13", "fru_state": "6"},
    "FPC: QFX10002-72Q 0": {"fru_type": "3", "fru_state": "6"},
    "PIC: 72X40G 0/0": {"fru_type": "11", "fru_state": "6"},
    "Routing Engine 0": {"fru_type": "6", "fru_state": "6"},
}


def test_parse_juniper_fru() -> None:
    assert (
        parse_juniper_fru(
            [
                ["Power Supply 0", "7", "6"],
                ["Power Supply 1", "7", "3"],
                ["Fan Tray 0 Fan 0", "13", "6"],
                ["Fan Tray 0 Fan 1", "13", "6"],
                ["Fan Tray 1 Fan 0", "13", "6"],
                ["Fan Tray 1 Fan 1", "13", "6"],
                ["Fan Tray 2 Fan 0", "13", "6"],
                ["Fan Tray 2 Fan 1", "13", "6"],
                ["FPC: QFX10002-72Q @ 0/*/*", "3", "6"],
                ["PIC: 72X40G @ 0/0/*", "11", "6"],
                ["Routing Engine 0", "6", "6"],
            ]
        )
        == _SECTION
    )


def test_check_juniper_fru_online() -> None:
    assert list(check_juniper_fru("Power Supply 0", _SECTION)) == [
        Result(state=State.OK, summary="Operational status: online"),
    ]


def test_check_juniper_fru_present() -> None:
    assert list(check_juniper_fru("Power Supply 1", _SECTION)) == [
        Result(state=State.WARN, summary="Operational status: present"),
    ]
