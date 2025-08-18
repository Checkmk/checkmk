#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import aruba_sw_temp

DATA = [
    [
        "1.3.1.1",
        "1/1-PHY-01-08",
        "emergency",
        "79000",
        "35000",
        "81000",
    ],
    [
        "1.3.1.2",
        "1/1-PHY-09-16",
        "normal",
        "92000",
        "35000",
        "93000",
    ],
    [
        "1.3.1.3",
        "1/1-PHY-17-24",
        "normal",
        "83000",
        "35000",
        "85000",
    ],
    [
        "1.3.1.4",
        "1/1-Inlet-Air",
        "normal",
        "27875",
        "17000",
        "31000",
    ],
    [
        "1.3.1.5",
        "1/1-Switch-ASIC-Internal",
        "normal",
        "62000",
        "50000",
        "65000",
    ],
    [
        "1.3.1.6",
        "1/1-Switch-CPU-1",
        "normal",
        "61625",
        "50000",
        "65000",
    ],
    [
        "1.3.1.7",
        "1/1-Switch-CPU-2",
        "fault",
        "63125",
        "50000",
        "65000",
    ],
    [
        "1.3.1.8",
        "1/1-Switch-DDR-1",
        "normal",
        "50000",
        "40000",
        "55000",
    ],
    [
        "1.3.1.8",
        "1/1-Switch-DDR-Inlet-1",
        "normal",
        "35000",
        "22000",
        "40000",
    ],
    [
        "1.3.1.8",
        "1/1-Switch-Mainboard",
        "normal",
        "30000",
        "25000",
        "35000",
    ],
    [
        "1.3.1.8",
        "1/1-Internal",
        "normal",
        "39000",
        "22000",
        "55000",
    ],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            DATA,
            [
                Service(item="1/1-PHY-01-08"),
                Service(item="1/1-PHY-09-16"),
                Service(item="1/1-PHY-17-24"),
                Service(item="1/1-Inlet-Air"),
                Service(item="1/1-Switch-ASIC-Internal"),
                Service(item="1/1-Switch-CPU-1"),
                Service(item="1/1-Switch-CPU-2"),
                Service(item="1/1-Switch-DDR-1"),
                Service(item="1/1-Switch-DDR-Inlet-1"),
                Service(item="1/1-Switch-Mainboard"),
                Service(item="1/1-Internal"),
            ],
        ),
    ],
)
def test_discover_aruba_sw_temp_status(
    string_table: StringTable,
    result: DiscoveryResult,
) -> None:
    section = aruba_sw_temp.parse_aruba_sw_temp(string_table)
    assert list(aruba_sw_temp.discover_aruba_sw_temp(section)) == result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "1/1-PHY-01-08",
            [
                Metric(
                    "temp",
                    79.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.PHY, aruba_sw_temp.SensorCritTemp.PHY),
                ),
                Result(state=State.OK, summary="Temperature: 79.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.CRIT, summary="Device status: emergency"),
                Result(state=State.OK, summary="Min temperature: 35.0 °C"),
                Result(state=State.OK, summary="Max temperature: 81.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-PHY-09-16",
            [
                Metric(
                    "temp",
                    92.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.PHY, aruba_sw_temp.SensorCritTemp.PHY),
                ),
                Result(state=State.CRIT, summary="Temperature: 92.0 °C (warn/crit at 80 °C/90 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 35.0 °C"),
                Result(state=State.OK, summary="Max temperature: 93.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-PHY-17-24",
            [
                Metric(
                    "temp",
                    83.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.PHY, aruba_sw_temp.SensorCritTemp.PHY),
                ),
                Result(state=State.WARN, summary="Temperature: 83.0 °C (warn/crit at 80 °C/90 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 35.0 °C"),
                Result(state=State.OK, summary="Max temperature: 85.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Inlet-Air",
            [
                Metric(
                    "temp",
                    27.875,
                    levels=(aruba_sw_temp.SensorWarnTemp.INLET, aruba_sw_temp.SensorCritTemp.INLET),
                ),
                Result(state=State.OK, summary="Temperature: 27.9 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 17.0 °C"),
                Result(state=State.OK, summary="Max temperature: 31.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-ASIC-Internal",
            [
                Metric(
                    "temp",
                    62.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.ASIC, aruba_sw_temp.SensorCritTemp.ASIC),
                ),
                Result(state=State.OK, summary="Temperature: 62.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 50.0 °C"),
                Result(state=State.OK, summary="Max temperature: 65.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-CPU-1",
            [
                Metric(
                    "temp",
                    61.625,
                    levels=(aruba_sw_temp.SensorWarnTemp.CPU, aruba_sw_temp.SensorCritTemp.CPU),
                ),
                Result(state=State.OK, summary="Temperature: 61.6 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 50.0 °C"),
                Result(state=State.OK, summary="Max temperature: 65.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-CPU-2",
            [
                Result(state=State.WARN, summary="Device status: fault"),
                Result(state=State.OK, summary="Min temperature: 50.0 °C"),
                Result(state=State.OK, summary="Max temperature: 65.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-DDR-1",
            [
                Metric(
                    "temp",
                    50.000,
                    levels=(aruba_sw_temp.SensorWarnTemp.DDR, aruba_sw_temp.SensorCritTemp.DDR),
                ),
                Result(state=State.OK, summary="Temperature: 50.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 40.0 °C"),
                Result(state=State.OK, summary="Max temperature: 55.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-DDR-Inlet-1",
            [
                Metric(
                    "temp",
                    35.000,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.DDR_INLET,
                        aruba_sw_temp.SensorCritTemp.DDR_INLET,
                    ),
                ),
                Result(state=State.OK, summary="Temperature: 35.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 22.0 °C"),
                Result(state=State.OK, summary="Max temperature: 40.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-Mainboard",
            [
                Metric(
                    "temp",
                    30.000,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.MAINBOARD,
                        aruba_sw_temp.SensorCritTemp.MAINBOARD,
                    ),
                ),
                Result(state=State.OK, summary="Temperature: 30.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 35.0 °C"),
            ],
        ),
        (
            DATA,
            "1/1-Internal",
            [
                Metric(
                    "temp",
                    39.000,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.INTERNAL,
                        aruba_sw_temp.SensorCritTemp.INTERNAL,
                    ),
                ),
                Result(state=State.OK, summary="Temperature: 39.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 22.0 °C"),
                Result(state=State.OK, summary="Max temperature: 55.0 °C"),
            ],
        ),
    ],
)
def test_check_aruba_fan_status(
    string_table: StringTable,
    item: str,
    result: CheckResult,
) -> None:
    section = aruba_sw_temp.parse_aruba_sw_temp(string_table)
    assert (
        list(
            aruba_sw_temp.check_aruba_sw_temp(
                item,
                aruba_sw_temp.aruba_sw_temp_check_default_parameters,
                section,
            )
        )
        == result
    )
