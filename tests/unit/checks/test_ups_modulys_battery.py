#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="check")
def _ups_modulys_battery_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("ups_modulys_battery")]


@pytest.fixture(name="temp_check")
def _ups_modulys_battery_temp_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("ups_modulys_battery_temp")]


@pytest.fixture(name="string_table")
def _string_table() -> StringTable:
    return [
        [
            "1",  # battery_health
            "0",  # elapsed_sec
            "10",  # remaining_min
            "80",  # battery_capacity
            "45",  # battery_temperature
        ],
    ]


def test_discover_ups_modulys_battery(check: CheckPlugin, string_table: StringTable) -> None:
    assert list(check.discovery_function(string_table)) == [Service()]


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            [["0", "0", "10", "100", "45"]],
            [Result(state=State.OK, summary="on mains")],
            id="Everything is OK",
        ),
        pytest.param(
            [["0", "60", "10", "100", "45"]],
            [Result(state=State.OK, summary="discharging for 1 minutes")],
            id="If the elapsed time is not 0, the desciption gives information in how many minutes the battery will discharge.",
        ),
        pytest.param(
            [["1", "0", "10", "100", "45"]],
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.WARN, summary="battery health weak"),
            ],
            id="If the battery health is 1, the check result is a WARN state and description that tells that the battery is weak.",
        ),
        pytest.param(
            [["2", "0", "10", "100", "45"]],
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.CRIT, summary="battery needs to be replaced"),
            ],
            id="If the battery health is 2, the check result is a CRIT state and description that tells that the battery needs to be replaced.",
        ),
        pytest.param(
            [["0", "0", "10", "80", "45"]],
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.WARN, summary="80 percent charged (warn/crit at 95/90 perc)"),
            ],
            id="If the remaining capacity is less than the warn/crit levels, the check result state is WARN with the appropriate description.",
        ),
        pytest.param(
            [["0", "2", "8", "100", "45"]],
            [
                Result(state=State.OK, summary="discharging for 0 minutes"),
                Result(state=State.WARN, summary="8 minutes remaining (warn/crit at 9/7 min)"),
            ],
            id="If the remaining time is less than the warn level, the check result state is WARN with the appropriate description. The elapsed time must not be 0.",
        ),
        pytest.param(
            [["0", "2", "5", "100", "45"]],
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
    section: StringTable,
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


def test_discover_ups_modulys_battery_temp(
    temp_check: CheckPlugin, string_table: StringTable
) -> None:
    assert list(temp_check.discovery_function(string_table)) == [Service(item="Battery")]


def test_check_ups_modulys_battery_temp_ok_state(
    temp_check: CheckPlugin, string_table: StringTable
) -> None:
    assert list(
        temp_check.check_function(
            item="test",
            params={"levels": (90, 95)},
            section=string_table,
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
            section=[["0", "0", "10", "100", "92"]],
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
            section=[["0", "0", "10", "100", "96"]],
        ),
    ) == [
        Result(state=State.CRIT, summary="96 °C (warn/crit at 90/95 °C)"),
        Metric("temp", 96.0, levels=(90.0, 95.0)),
    ]


def test_check_ups_modulys_battery_temp_no_input(temp_check: CheckPlugin) -> None:
    assert (
        list(
            temp_check.check_function(
                item="test",
                params={"levels": (90, 95)},
                section=[],
            ),
        )
        == []
    )
