#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.lib.temperature import TempParamType
from cmk.plugins.vutlan.agent_based.vutlan_ems_temp import (
    check_vutlan_ems_temp_impl,
    discover_vutlan_ems_temp,
    parse_vutlan_ems_temp,
)

STRING_TABLE = [
    ["101001", "Dry-1", "0"],
    ["101002", "Dry-2", "0"],
    ["101003", "Dry-3", "0"],
    ["101004", "Dry-4", "0"],
    ["106001", "Analog-5", "0"],
    ["107001", "Analog-6", "0"],
    ["201001", "Onboard Temperature", "32.80"],
    ["201002", "Analog-1", "22.00"],
    ["201003", "Analog-2", "22.10"],
    ["201004", "Zero-Analog", "0.00"],
    ["202001", "Analog-3", "46.20"],
    ["202002", "Analog-4", "42.10"],
    ["203001", "Onboard Voltage DC", "12.06"],
    ["301001", "Analog Power", "on"],
    ["304001", "Power-1", "off"],
    ["304002", "Power-2", "off"],
    ["403001", "USB Web camera", "0"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            STRING_TABLE,
            [
                Service(item="Analog-1"),
                Service(item="Analog-2"),
                Service(item="Zero-Analog"),
                Service(item="Onboard Temperature"),
            ],
        ),
    ],
)
def test_discover_vutlan_ems_temp(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    section = parse_vutlan_ems_temp(string_table)
    result = list(discover_vutlan_ems_temp(section))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        (
            "Analog-1",
            {"levels": (80.0, 90.0)},
            [
                Metric("temp", 22.0, levels=(80.0, 90.0)),
                Result(state=State.OK, summary="Temperature: 22.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
        ),
        (
            "Analog-2",
            {"levels": (10.0, 20.0)},
            [
                Metric("temp", 22.1, levels=(10.0, 20.0)),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 22.1 °C (warn/crit at 10.0 °C/20.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
        ),
        (
            "Onboard Temperature",
            {"levels": (80.0, 90.0)},
            [
                Metric("temp", 32.8, levels=(80.0, 90.0)),
                Result(state=State.OK, summary="Temperature: 32.8 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
        ),
    ],
)
def testcheck_vutlan_ems_temp_impl(
    item: str, params: TempParamType, expected_results: CheckResult
) -> None:
    section = parse_vutlan_ems_temp(STRING_TABLE)
    result = list(check_vutlan_ems_temp_impl(item, params, section, {}))
    assert result == expected_results


def testcheck_vutlan_ems_temp_impl_reports_zero_degree_reading() -> None:
    """A 0.0 °C reading used to be treated as falsy and silently skipped."""
    section = parse_vutlan_ems_temp(STRING_TABLE)
    result = list(check_vutlan_ems_temp_impl("Zero-Analog", {"levels": (80.0, 90.0)}, section, {}))
    assert result == [
        Metric("temp", 0.0, levels=(80.0, 90.0)),
        Result(state=State.OK, summary="Temperature: 0.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]
