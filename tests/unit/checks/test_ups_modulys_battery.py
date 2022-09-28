#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


class UPSBattery(NamedTuple):
    health: int
    uptime: int
    remaining_time_in_min: int
    capacity: int
    temperature: int | None


UPSBatterySection = UPSBattery | None


@pytest.fixture(name="temp_check")
def _ups_modulys_battery_temp_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("ups_modulys_battery_temp")]


def test_discover_ups_modulys_battery_temp(temp_check: CheckPlugin) -> None:
    assert list(
        temp_check.discovery_function(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            )
        )
    ) == [Service(item="Battery")]


def test_discover_ups_modulys_battery_temp_is_zero(temp_check: CheckPlugin) -> None:
    assert list(
        temp_check.discovery_function(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=0,
            )
        )
    ) == [Service(item="Battery")]


def test_discover_ups_modulys_battery_temp_no_services_discovered(temp_check: CheckPlugin) -> None:
    assert list(temp_check.discovery_function(None)) == []

    assert (
        list(
            temp_check.discovery_function(
                UPSBattery(
                    health=0,
                    uptime=0,
                    remaining_time_in_min=10,
                    capacity=100,
                    temperature=None,
                )
            )
        )
        == []
    )


def test_check_ups_modulys_battery_temp_ok_state(temp_check: CheckPlugin) -> None:
    assert list(
        temp_check.check_function(
            item="test",
            params={"levels": (90, 95)},
            section=UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
        ),
    ) == [
        Result(state=State.OK, summary="45 °C"),
        Metric("temp", 45.0, levels=(90.0, 95.0)),
    ]


def test_check_ups_modulys_battery_temp_warn_state(temp_check: CheckPlugin) -> None:
    assert list(
        temp_check.check_function(
            item="test",
            params={"levels": (90, 95)},
            section=UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=92,
            ),
        ),
    ) == [
        Result(state=State.WARN, summary="92 °C (warn/crit at 90/95 °C)"),
        Metric("temp", 92.0, levels=(90.0, 95.0)),
    ]


def test_check_ups_modulys_battery_temp_crit_state(temp_check: CheckPlugin) -> None:
    assert list(
        temp_check.check_function(
            item="test",
            params={"levels": (90, 95)},
            section=UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=96,
            ),
        ),
    ) == [
        Result(state=State.CRIT, summary="96 °C (warn/crit at 90/95 °C)"),
        Metric("temp", 96.0, levels=(90.0, 95.0)),
    ]
