#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.bluecoat_sensors import (
    check_bluecoat_sensors,
    check_bluecoat_sensors_temp,
    discover_bluecoat_sensors,
    discover_bluecoat_sensors_temp,
    parse_bluecoat_sensors,
    Section,
    Sensor,
    VoltageSensor,
)

_SECTION = Section(
    temperature_sensors={
        "DIMM A1": Sensor(value=30.0, is_ok=True),
        "DIMM A2": Sensor(value=30.0, is_ok=True),
        "PCH": Sensor(value=45.0, is_ok=True),
        "SAS controller": Sensor(value=37.0, is_ok=True),
        "SSL card": Sensor(value=26.0, is_ok=False),
        "System center": Sensor(value=37.0, is_ok=True),
        "System left": Sensor(value=30.0, is_ok=True),
        "System right": Sensor(value=33.0, is_ok=True),
        "CPU": Sensor(value=39.0, is_ok=True),
    },
    other_sensors={
        "System fan 1 front speed": Sensor(value=8100.0, is_ok=True),
        "System fan 1 rear speed": Sensor(value=6800.0, is_ok=True),
        "+3.3V main bus voltage": VoltageSensor(value=3.244, is_ok=True),
        "+3.3V standby voltage": VoltageSensor(value=3.1990000000000003, is_ok=True),
        "+5V main bus voltage": VoltageSensor(value=5.050800000000001, is_ok=True),
        "+5V standby voltage": VoltageSensor(value=5.050800000000001, is_ok=True),
        "BMC PLL voltage": VoltageSensor(value=1.264, is_ok=True),
        "CPU core voltage": VoltageSensor(value=0.8428, is_ok=True),
        "CPU PLL voltage": VoltageSensor(value=1.8326, is_ok=True),
        "CPU system agent voltage": VoltageSensor(value=0.931, is_ok=True),
        "CPU termination voltage": VoltageSensor(value=1.064, is_ok=True),
        "Memory I/O voltage": VoltageSensor(value=1.52, is_ok=True),
        "Memory termination voltage": VoltageSensor(value=0.752, is_ok=True),
        "PCH core voltage": VoltageSensor(value=1.112, is_ok=True),
        "PCH SAS voltage": VoltageSensor(value=1.52, is_ok=True),
        "SAS core voltage": VoltageSensor(value=1.04, is_ok=True),
        "SAS I/O voltage": VoltageSensor(value=1.8326, is_ok=True),
        "SSL core voltage": VoltageSensor(value=0.904, is_ok=False),
        "SSL PLL voltage": VoltageSensor(value=1.8, is_ok=False),
        "SSL VPTX voltage": VoltageSensor(value=1.8, is_ok=False),
        "Power supply 1 status": Sensor(value=8.0, is_ok=True),
        "Power supply 2 status": Sensor(value=8.0, is_ok=True),
    },
)


def test_parse_bluecoat_sensors() -> None:
    assert (
        parse_bluecoat_sensors(
            [
                ["DIMM A1 temperature", "30", "1", "0", "5"],
                ["DIMM A2 temperature", "30", "1", "0", "5"],
                ["PCH temperature", "45", "1", "0", "5"],
                ["SAS controller temperature", "37", "1", "0", "5"],
                ["SSL card temperature", "26", "4", "0", "5"],
                ["System center temperature", "37", "1", "0", "5"],
                ["System left temperature", "30", "1", "0", "5"],
                ["System right temperature", "33", "1", "0", "5"],
                ["CPU temperature", "39", "1", "0", "5"],
                ["System fan 1 front speed", "8100", "1", "0", "6"],
                ["System fan 1 rear speed", "6800", "1", "0", "6"],
                ["+3.3V main bus voltage", "3244", "1", "-3", "4"],
                ["+3.3V standby voltage", "3199", "1", "-3", "4"],
                ["+5V main bus voltage", "50508", "1", "-4", "4"],
                ["+5V standby voltage", "50508", "1", "-4", "4"],
                ["BMC PLL voltage", "1264", "1", "-3", "4"],
                ["CPU core voltage", "8428", "1", "-4", "4"],
                ["CPU PLL voltage", "18326", "1", "-4", "4"],
                ["CPU system agent voltage", "9310", "1", "-4", "4"],
                ["CPU termination voltage", "1064", "1", "-3", "4"],
                ["Memory I/O voltage", "1520", "1", "-3", "4"],
                ["Memory termination voltage", "752", "1", "-3", "4"],
                ["PCH core voltage", "1112", "1", "-3", "4"],
                ["PCH SAS voltage", "1520", "1", "-3", "4"],
                ["SAS core voltage", "1040", "1", "-3", "4"],
                ["SAS I/O voltage", "18326", "1", "-4", "4"],
                ["SSL core voltage", "904", "4", "-3", "4"],
                ["SSL PLL voltage", "1800", "4", "-3", "4"],
                ["SSL VPTX voltage", "1800", "4", "-3", "4"],
                ["Power supply 1 status", "8", "1", "0", "3"],
                ["Power supply 2 status", "8", "1", "0", "3"],
            ]
        )
        == _SECTION
    )


def test_discover_bluecoat_sensors() -> None:
    assert list(discover_bluecoat_sensors(_SECTION)) == [
        Service(item="System fan 1 front speed"),
        Service(item="System fan 1 rear speed"),
        Service(item="+3.3V main bus voltage"),
        Service(item="+3.3V standby voltage"),
        Service(item="+5V main bus voltage"),
        Service(item="+5V standby voltage"),
        Service(item="BMC PLL voltage"),
        Service(item="CPU core voltage"),
        Service(item="CPU PLL voltage"),
        Service(item="CPU system agent voltage"),
        Service(item="CPU termination voltage"),
        Service(item="Memory I/O voltage"),
        Service(item="Memory termination voltage"),
        Service(item="PCH core voltage"),
        Service(item="PCH SAS voltage"),
        Service(item="SAS core voltage"),
        Service(item="SAS I/O voltage"),
        Service(item="SSL core voltage"),
        Service(item="SSL PLL voltage"),
        Service(item="SSL VPTX voltage"),
        Service(item="Power supply 1 status"),
        Service(item="Power supply 2 status"),
    ]


@pytest.mark.parametrize(
    [
        "item",
        "expected_result",
    ],
    [
        pytest.param(
            "+3.3V main bus voltage",
            [
                Result(state=State.OK, summary="3.2 V"),
                Metric("voltage", 3.244),
            ],
            id="voltage ok",
        ),
        pytest.param(
            "SSL VPTX voltage",
            [
                Result(state=State.CRIT, summary="1.8 V"),
                Metric("voltage", 1.8),
            ],
            id="voltage crit",
        ),
        pytest.param(
            "System fan 1 front speed",
            [
                Result(state=State.OK, summary="8100.0"),
            ],
            id="fan_speed",
        ),
        pytest.param(
            "Power supply 1 status",
            [
                Result(state=State.OK, summary="8.0"),
            ],
            id="supply_status",
        ),
    ],
)
def test_check_bluecoat_sensors(
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_bluecoat_sensors(
                item=item,
                section=_SECTION,
            )
        )
        == expected_result
    )


def test_discover_bluecoat_sensors_temp() -> None:
    assert list(discover_bluecoat_sensors_temp(_SECTION)) == [
        Service(item="DIMM A1"),
        Service(item="DIMM A2"),
        Service(item="PCH"),
        Service(item="SAS controller"),
        Service(item="SSL card"),
        Service(item="System center"),
        Service(item="System left"),
        Service(item="System right"),
        Service(item="CPU"),
    ]


@pytest.mark.parametrize(
    [
        "item",
        "expected_result",
    ],
    [
        pytest.param(
            "System center",
            [
                Metric("temp", 37.0),
                Result(state=State.OK, summary="Temperature: 37.0°C"),
                Result(state=State.OK, notice="State on device: OK"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer device levels over user levels (no levels found)",
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "SSL card",
            [
                Metric("temp", 26.0),
                Result(state=State.OK, summary="Temperature: 26.0°C"),
                Result(state=State.CRIT, summary="State on device: Not OK"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer device levels over user levels (no levels found)",
                ),
            ],
            id="crit",
        ),
    ],
)
def test_check_bluecoat_sensors_temp(
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_bluecoat_sensors_temp(
                item=item,
                params={"device_levels_handling": "devdefault"},
                section=_SECTION,
            )
        )
        == expected_result
    )
