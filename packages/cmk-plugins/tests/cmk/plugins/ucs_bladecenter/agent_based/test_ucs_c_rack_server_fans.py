#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based.ucs_c_rack_server_fans import (
    check_ucs_c_rack_server_fans,
    discover_ucs_c_rack_server_fans,
    parse_ucs_c_rack_server_fans,
)


def _fan(rack: int, fan: int, operability: str) -> list[str]:
    return [
        "equipmentFan",
        f"dn sys/rack-unit-{rack}/fan-module-1-1/fan-{fan}",
        f"id {fan}",
        "model ",
        f"operability {operability}",
    ]


_SECTION = parse_ucs_c_rack_server_fans(
    [
        _fan(1, 1, "operable"),
        _fan(1, 2, "inoperable"),
        _fan(2, 1, "unknown"),
        _fan(2, 2, "bogus"),
        ["equipmentFan", "dn sys/rack-unit-3/fan-module-1-1/fan-1"],  # incomplete, skipped
    ]
)


def test_discover_ucs_c_rack_server_fans() -> None:
    assert list(discover_ucs_c_rack_server_fans(_SECTION)) == [
        Service(item="Rack Unit 1 Module 1-1 1"),
        Service(item="Rack Unit 1 Module 1-1 2"),
        Service(item="Rack Unit 2 Module 1-1 1"),
        Service(item="Rack Unit 2 Module 1-1 2"),
    ]


def test_check_ucs_c_rack_server_fans() -> None:
    assert list(check_ucs_c_rack_server_fans("Rack Unit 1 Module 1-1 1", _SECTION)) == [
        Result(state=State.OK, summary="Operability Status is operable")
    ]
    assert list(check_ucs_c_rack_server_fans("Rack Unit 1 Module 1-1 2", _SECTION)) == [
        Result(state=State.CRIT, summary="Operability Status is inoperable")
    ]
    assert list(check_ucs_c_rack_server_fans("Rack Unit 2 Module 1-1 1", _SECTION)) == [
        Result(state=State.UNKNOWN, summary="Operability Status is unknown")
    ]


def test_check_ucs_c_rack_server_fans_unmapped_value() -> None:
    assert list(check_ucs_c_rack_server_fans("Rack Unit 2 Module 1-1 2", _SECTION)) == [
        Result(state=State.UNKNOWN, summary="Unknown Operability Status: bogus")
    ]


def test_check_ucs_c_rack_server_fans_vanished_item() -> None:
    assert not list(check_ucs_c_rack_server_fans("Rack Unit 3 Module 1-1 1", _SECTION))
