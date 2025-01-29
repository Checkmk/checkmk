#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.apc_netbotz_other_sensors import (
    check_apc_netbotz_other_sensors,
    discover_apc_netbotz_other_sensors,
    parse_apc_netbotz_other_sensors,
)

TEST_INFO: StringTable = [
    ["Ethernet Link Status", "0", "Up"],
    ["A-Link Bus Power", "0", "OK"],
    ["Sensor A", "1", "Error"],
]


def test_inventory_apc_netbotz_other_sensors() -> None:
    section = parse_apc_netbotz_other_sensors(TEST_INFO)
    result = list(discover_apc_netbotz_other_sensors(section))
    assert result == [Service()]


def test_check_apc_netbotz_other_sensors() -> None:
    section = parse_apc_netbotz_other_sensors(TEST_INFO)
    result = list(check_apc_netbotz_other_sensors(section=section))
    assert result == [
        Result(state=State.CRIT, summary="Sensor A: error"),
        Result(state=State.OK, summary="2 sensors are OK"),
    ]
