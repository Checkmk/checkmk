#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based.ucs_c_rack_server_psu import (
    check_ucs_c_rack_server_psu,
    check_ucs_c_rack_server_psu_voltage,
    discover_ucs_c_rack_server_psu,
    discover_ucs_c_rack_server_psu_voltage,
    parse_ucs_c_rack_server_psu,
)


def _psu(rack: int, psu: int, model: str, operability: str, voltage: str) -> list[str]:
    return [
        "equipmentPsu",
        f"dn sys/rack-unit-{rack}/psu-{psu}",
        f"id {psu}",
        f"model {model}",
        f"operability {operability}",
        f"voltage {voltage}",
    ]


_SECTION = parse_ucs_c_rack_server_psu(
    [
        _psu(1, 1, "blabla", "operable", "upper-critical"),
        _psu(1, 2, "blabla", "inoperable", "ok"),
        _psu(2, 1, "UCS-PSU-6332-AC", "operable", "unknown"),
        _psu(2, 2, "other", "bogus", "bogus"),
        ["equipmentPsu", "dn sys/rack-unit-3/psu-1", "id 1"],  # incomplete, skipped
    ]
)


def test_discover_ucs_c_rack_server_psu() -> None:
    assert list(discover_ucs_c_rack_server_psu(_SECTION)) == [
        Service(item="Rack Unit 1 PSU 1"),
        Service(item="Rack Unit 1 PSU 2"),
        Service(item="Rack Unit 2 PSU 1"),
        Service(item="Rack Unit 2 PSU 2"),
    ]


def test_discover_ucs_c_rack_server_psu_voltage_skips_unknown_ucs() -> None:
    # UCS- models reporting an unknown voltage have no voltage sensor, see SUP-11285.
    assert list(discover_ucs_c_rack_server_psu_voltage(_SECTION)) == [
        Service(item="Rack Unit 1 PSU 1"),
        Service(item="Rack Unit 1 PSU 2"),
        Service(item="Rack Unit 2 PSU 2"),
    ]


def test_check_ucs_c_rack_server_psu() -> None:
    assert list(check_ucs_c_rack_server_psu("Rack Unit 1 PSU 1", _SECTION)) == [
        Result(state=State.OK, summary="Status: operable")
    ]
    assert list(check_ucs_c_rack_server_psu("Rack Unit 1 PSU 2", _SECTION)) == [
        Result(state=State.CRIT, summary="Status: inoperable")
    ]


def test_check_ucs_c_rack_server_psu_unmapped_value() -> None:
    assert list(check_ucs_c_rack_server_psu("Rack Unit 2 PSU 2", _SECTION)) == [
        Result(state=State.UNKNOWN, summary="Status: unknown[bogus]")
    ]


def test_check_ucs_c_rack_server_psu_voltage() -> None:
    assert list(check_ucs_c_rack_server_psu_voltage("Rack Unit 1 PSU 1", _SECTION)) == [
        Result(state=State.CRIT, summary="Status: upper-critical")
    ]
    assert list(check_ucs_c_rack_server_psu_voltage("Rack Unit 1 PSU 2", _SECTION)) == [
        Result(state=State.OK, summary="Status: ok")
    ]


def test_check_ucs_c_rack_server_psu_voltage_unmapped_value() -> None:
    assert list(check_ucs_c_rack_server_psu_voltage("Rack Unit 2 PSU 2", _SECTION)) == [
        Result(state=State.UNKNOWN, summary="Status: unknown[bogus]")
    ]


def test_check_ucs_c_rack_server_psu_vanished_item() -> None:
    assert not list(check_ucs_c_rack_server_psu("Rack Unit 3 PSU 1", _SECTION))
    assert not list(check_ucs_c_rack_server_psu_voltage("Rack Unit 3 PSU 1", _SECTION))
