#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.dell_om_processors import (
    check_dell_om_processors,
    inventory_dell_om_processors,
    parse_dell_om_processors,
)

Section = StringTable

INFO = [
    ["1", "1", "Some manufacturer", "1", "0"],
    ["2", "2", "Some manufacturer", "2", "1"],
    ["3", "3", "Some manufacturer", "3", "2"],
    ["4", "4", "Some manufacturer", "4", "32"],
    ["5", "4", "Some manufacturer", "5", "128"],
    ["6", "5", "Some manufacturer", "6", "256"],
    ["7", "6", "Some manufacturer", "7", "512"],
    ["8", "6", "Some manufacturer", "8", "1024"],
]


def _section() -> Section:
    return parse_dell_om_processors(INFO)


def test_discovery() -> None:
    assert list(inventory_dell_om_processors(_section())) == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
        Service(item="6"),
        Service(item="7"),
        Service(item="8"),
    ]


def test_check_unknown() -> None:
    assert list(check_dell_om_processors("1", _section())) == [
        Result(
            state=State.CRIT, summary="[Some manufacturer] CPU status: Other, CPU reading: Unknown"
        )
    ]


def test_check_unknown2() -> None:
    assert list(check_dell_om_processors("4", _section())) == [
        Result(
            state=State.CRIT,
            summary="[Some manufacturer] CPU status: User Disabled, CPU reading: Configuration Error",
        )
    ]


def test_check_error() -> None:
    assert list(check_dell_om_processors("2", _section())) == [
        Result(
            state=State.CRIT,
            summary="[Some manufacturer] CPU status: Unknown, CPU reading: Internal Error",
        )
    ]


def test_check_enabled() -> None:
    assert list(check_dell_om_processors("3", _section())) == [
        Result(
            state=State.OK,
            summary="[Some manufacturer] CPU status: Enabled, CPU reading: Thermal Trip",
        )
    ]


def test_check_diabled() -> None:
    assert list(check_dell_om_processors("6", _section())) == [
        Result(
            state=State.CRIT,
            summary="[Some manufacturer] CPU status: BIOS Disabled, CPU reading: Disabled",
        )
    ]


def test_check_idle() -> None:
    assert list(check_dell_om_processors("8", _section())) == [
        Result(
            state=State.CRIT, summary="[Some manufacturer] CPU status: Idle, CPU reading: Throttled"
        )
    ]
