#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
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


@pytest.fixture(name="check")
def _ups_modulys_battery_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("ups_modulys_battery")]


@pytest.fixture(name="temp_check")
def _ups_modulys_battery_temp_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("ups_modulys_battery_temp")]


def test_discover_ups_modulys_battery(check: CheckPlugin) -> None:
    assert list(
        check.discovery_function(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            )
        )
    ) == [Service()]


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [Result(state=State.OK, summary="on mains")],
            id="Everything is OK",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=60,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [Result(state=State.OK, summary="discharging for 1 minutes")],
            id="If the elapsed time is not 0, the desciption gives information in how many minutes the battery will discharge.",
        ),
        pytest.param(
            UPSBattery(
                health=1,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.WARN, summary="battery health weak"),
            ],
            id="If the battery health is 1, the check result is a WARN state and description that tells that the battery is weak.",
        ),
        pytest.param(
            UPSBattery(
                health=2,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.CRIT, summary="battery needs to be replaced"),
            ],
            id="If the battery health is 2, the check result is a CRIT state and description that tells that the battery needs to be replaced.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=80,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.CRIT, summary="80 percent charged (warn/crit at 95/90 perc)"),
            ],
            id="If the remaining capacity is less than the crit level, the check result state is CRIT with the appropriate description.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=92,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.WARN, summary="92 percent charged (warn/crit at 95/90 perc)"),
            ],
            id="If the remaining capacity is less than the warn level, the check result state is WARN with the appropriate description.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=2,
                remaining_time_in_min=8,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="discharging for 0 minutes"),
                Result(state=State.WARN, summary="8 minutes remaining (warn/crit at 9/7 min)"),
            ],
            id="If the remaining time is less than the warn level, the check result state is WARN with the appropriate description. The elapsed time must not be 0.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=2,
                remaining_time_in_min=5,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="discharging for 0 minutes"),
                Result(state=State.CRIT, summary="5 minutes remaining (warn/crit at 9/7 min)"),
            ],
            id="If the remaining time is less than the crit level, the check result state is CRIT with the appropriate description. The elapsed time must not be 0.",
        ),
    ],
)
def test_check_ups_modulys_battery(
    check: CheckPlugin,
    section: UPSBatterySection,
    expected_result: Sequence[Result],
) -> None:
    assert (
        list(
            check.check_function(
                item="", params={"capacity": (95, 90), "battime": (9, 7)}, section=section
            )
        )
        == expected_result
    )


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
