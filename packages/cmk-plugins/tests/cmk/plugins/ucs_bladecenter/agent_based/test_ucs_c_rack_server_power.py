#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based.ucs_c_rack_server_power import (
    check_ucs_c_rack_server_power,
    discover_ucs_c_rack_server_power,
    parse_ucs_c_rack_server_power,
)


def _power(rack: int, consumed: str) -> list[str]:
    return [
        "computeMbPowerStats",
        f"dn sys/rack-unit-{rack}/board/power-stats",
        f"consumedPower {consumed}",
        "inputCurrent 6.00",
        "inputVoltage 12.100",
    ]


_SECTION = parse_ucs_c_rack_server_power([_power(1, "88"), _power(2, "95"), _power(3, "120")])
_PARAMS = {"power_upper_levels": (90, 100)}


def test_parse_ucs_c_rack_server_power_skips_uncastable_values() -> None:
    section = parse_ucs_c_rack_server_power([_power(1, "not-a-number")])
    assert section["Rack Unit 1"] == {"inputCurrent": 6.0, "inputVoltage": 12.1}


def test_discover_ucs_c_rack_server_power() -> None:
    assert list(discover_ucs_c_rack_server_power(_SECTION)) == [
        Service(item="Rack Unit 1"),
        Service(item="Rack Unit 2"),
        Service(item="Rack Unit 3"),
    ]


def test_check_ucs_c_rack_server_power() -> None:
    assert list(check_ucs_c_rack_server_power("Rack Unit 1", _PARAMS, _SECTION)) == [
        Result(state=State.OK, summary="Power: 88.0 W"),
        Metric("power", 88.0, levels=(90.0, 100.0)),
        Result(state=State.OK, summary="Current: 6.0 A"),
        Result(state=State.OK, summary="Voltage: 12.1 V"),
    ]


def test_check_ucs_c_rack_server_power_above_levels() -> None:
    assert list(check_ucs_c_rack_server_power("Rack Unit 3", _PARAMS, _SECTION))[:2] == [
        Result(state=State.CRIT, summary="Power: 120.0 W (warn/crit at 90.0 W/100.0 W)"),
        Metric("power", 120.0, levels=(90.0, 100.0)),
    ]


def test_check_ucs_c_rack_server_power_vanished_item() -> None:
    assert not list(check_ucs_c_rack_server_power("Rack Unit 4", _PARAMS, _SECTION))
