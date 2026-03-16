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
from cmk.plugins.aruba.agent_based import aruba_sw_temp

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
    [
        "1.3.1.9",
        "1/1-Fabric-IBC",
        "normal",
        "46000",  # Exceeds 45°C WARN
        "25000",
        "45000",
    ],
    [
        "1.3.1.10",
        "1/1-PCIE-Management",
        "normal",
        "56000",  # Exceeds 55°C WARN
        "30000",
        "55000",
    ],
    [
        "1.3.1.11",
        "1/3-Board-rear",
        "normal",
        "46000",  # Exceeds 45°C WARN
        "25000",
        "45000",
    ],
    [
        "1.3.1.12",
        "1/3-Exhaust-left",
        "normal",
        "47000",  # Exceeds 45°C WARN
        "25000",
        "45000",
    ],
    [
        "1.3.1.13",
        "1/1-Exhaust-Air",
        "normal",
        "48000",  # Exceeds 45°C WARN
        "25000",
        "45000",
    ],
    [
        "1.3.1.14",
        "1/3-IBC",
        "normal",
        "49000",  # Exceeds 45°C WARN
        "25000",
        "45000",
    ],
    [
        "1.3.1.15",
        "1/4-Switch-ASIC",
        "normal",
        "85000",  # Exceeds 80°C WARN
        "40000",
        "80000",
    ],
    [
        "1.3.1.16",
        "1/1-Board-NW",
        "normal",
        "38000",  # Exceeds 35°C WARN
        "20000",
        "35000",
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
                Service(item="1/1-Fabric-IBC"),
                Service(item="1/1-PCIE-Management"),
                Service(item="1/3-Board-rear"),
                Service(item="1/3-Exhaust-left"),
                Service(item="1/1-Exhaust-Air"),
                Service(item="1/3-IBC"),
                Service(item="1/4-Switch-ASIC"),
                Service(item="1/1-Board-NW"),
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


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.aruba.agent_based.aruba_sw_temp.get_value_store",
        lambda: {},
    )


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
        (
            [["1.3.1.9", "1/1-Fabric-IBC", "normal", "46000", "25000", "45000"]],
            "1/1-Fabric-IBC",
            [
                Metric(
                    "temp",
                    46.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.IBC, aruba_sw_temp.SensorCritTemp.IBC),
                ),
                Result(state=State.WARN, summary="Temperature: 46.0 °C (warn/crit at 45 °C/50 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 45.0 °C"),
            ],
        ),
        (
            [["1.3.1.10", "1/1-PCIE-Management", "normal", "56000", "30000", "55000"]],
            "1/1-PCIE-Management",
            [
                Metric(
                    "temp",
                    56.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.PCIE, aruba_sw_temp.SensorCritTemp.PCIE),
                ),
                Result(state=State.WARN, summary="Temperature: 56.0 °C (warn/crit at 55 °C/60 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 30.0 °C"),
                Result(state=State.OK, summary="Max temperature: 55.0 °C"),
            ],
        ),
        (
            [["1.3.1.11", "1/3-Board-rear", "normal", "46000", "25000", "45000"]],
            "1/3-Board-rear",
            [
                Metric(
                    "temp",
                    46.0,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.BOARD_REAR,
                        aruba_sw_temp.SensorCritTemp.BOARD_REAR,
                    ),
                ),
                Result(state=State.WARN, summary="Temperature: 46.0 °C (warn/crit at 45 °C/50 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 45.0 °C"),
            ],
        ),
        (
            [["1.3.1.12", "1/3-Exhaust-left", "normal", "47000", "25000", "45000"]],
            "1/3-Exhaust-left",
            [
                Metric(
                    "temp",
                    47.0,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.EXHAUST,
                        aruba_sw_temp.SensorCritTemp.EXHAUST,
                    ),
                ),
                Result(state=State.WARN, summary="Temperature: 47.0 °C (warn/crit at 45 °C/50 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 45.0 °C"),
            ],
        ),
        (
            [["1.3.1.13", "1/1-Exhaust-Air", "normal", "48000", "25000", "45000"]],
            "1/1-Exhaust-Air",
            [
                Metric(
                    "temp",
                    48.0,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.EXHAUST,
                        aruba_sw_temp.SensorCritTemp.EXHAUST,
                    ),
                ),
                Result(state=State.WARN, summary="Temperature: 48.0 °C (warn/crit at 45 °C/50 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 45.0 °C"),
            ],
        ),
        (
            [["1.3.1.14", "1/3-IBC", "normal", "49000", "25000", "45000"]],
            "1/3-IBC",
            [
                Metric(
                    "temp",
                    49.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.IBC, aruba_sw_temp.SensorCritTemp.IBC),
                ),
                Result(state=State.WARN, summary="Temperature: 49.0 °C (warn/crit at 45 °C/50 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 45.0 °C"),
            ],
        ),
        (
            [["1.3.1.15", "1/4-Switch-ASIC", "normal", "85000", "40000", "80000"]],
            "1/4-Switch-ASIC",
            [
                Metric(
                    "temp",
                    85.0,
                    levels=(aruba_sw_temp.SensorWarnTemp.ASIC, aruba_sw_temp.SensorCritTemp.ASIC),
                ),
                Result(state=State.WARN, summary="Temperature: 85.0 °C (warn/crit at 80 °C/90 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 40.0 °C"),
                Result(state=State.OK, summary="Max temperature: 80.0 °C"),
            ],
        ),
        (
            [["1.3.1.16", "1/1-Board-NW", "normal", "38000", "20000", "35000"]],
            "1/1-Board-NW",
            [
                Metric(
                    "temp",
                    38.0,
                    levels=(
                        aruba_sw_temp.SensorWarnTemp.MAINBOARD,
                        aruba_sw_temp.SensorCritTemp.MAINBOARD,
                    ),
                ),
                Result(state=State.WARN, summary="Temperature: 38.0 °C (warn/crit at 35 °C/40 °C)"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
                Result(state=State.OK, summary="Min temperature: 20.0 °C"),
                Result(state=State.OK, summary="Max temperature: 35.0 °C"),
            ],
        ),
    ],
)
def test_check_aruba_fan_status(
    string_table: StringTable,
    item: str,
    result: CheckResult,
    empty_value_store: None,
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
