#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.infoblox.agent_based.infoblox_temp import (
    check_temp,
    discover_infoblox_temp,
    snmp_section_infoblox_temp,
    TempDescr,
)
from cmk.plugins.lib.temperature import TempParamType

# SNMPSection (not Simple) - pass table directly (no wrapping needed)
TABLE_NIOS_7_2_7: Sequence[StringTable] = [
    [["", "7.2.7"]],
    [["", "5", "1", "1", "5", "1"]],
    [
        [
            "",
            "No power information available.",
            "The NTP service resumed synchronization.",
            "CPU_TEMP: +36.00 C",
            "No temperature information available.",
            "SYS_TEMP: +34.00 C",
        ]
    ],
]

TABLE_NIOS_9_0_3: Sequence[StringTable] = [
    [["", "9.0.3-50212"]],
    [["", "1", "5", "1", "5", "1"]],
    [
        [
            "",
            "CPU_TEMP: +36.00 C",
            "No temperature information available.",
            "SYS_TEMP: +34.00 C",
            "",
            "CPU Usage: 20%",
        ]
    ],
]


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param(TABLE_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(TABLE_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
def test_parse_infoblox_temp(string_table: Sequence[StringTable]) -> None:
    section = snmp_section_infoblox_temp.parse_function(string_table)
    assert section == {
        "CPU_TEMP 1": TempDescr(reading=36.0, state=(0, "working"), unit="c"),
        "SYS_TEMP": TempDescr(reading=34.0, state=(0, "working"), unit="c"),
    }


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param(TABLE_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(TABLE_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
def test_inventory_infoblox_temp(string_table: Sequence[StringTable]) -> None:
    section = snmp_section_infoblox_temp.parse_function(string_table)
    assert section is not None
    assert list(discover_infoblox_temp(section)) == [
        Service(item="CPU_TEMP 1"),
        Service(item="SYS_TEMP"),
    ]


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param(TABLE_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(TABLE_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "CPU_TEMP 1",
            {"levels": (40.0, 50.0)},
            [
                Metric(name="temp", value=36.0, levels=(40.0, 50.0)),
                Result(
                    state=State.OK,
                    summary="Temperature: 36.0 °C",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (30.0, 40.0)},
            [
                Metric(name="temp", value=34.0, levels=(30.0, 40.0)),
                Result(
                    state=State.WARN,
                    summary="Temperature: 34.0 °C (warn/crit at 30.0 °C/40.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="warning",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (20.0, 30.0)},
            [
                Metric(name="temp", value=34.0, levels=(20.0, 30.0)),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 34.0 °C (warn/crit at 20.0 °C/30.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="error",
        ),
    ],
)
def test_check_infoblox_temp(  # type: ignore[misc]
    string_table: Sequence[StringTable],
    item: str,
    params: TempParamType,
    expected: list,
) -> None:
    section = snmp_section_infoblox_temp.parse_function(string_table)
    assert section is not None

    assert list(check_temp(item, params, section, {})) == expected
