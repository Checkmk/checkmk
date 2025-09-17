#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.ucs_c_rack_server_power import (
    check_ucs_c_rack_server_power,
    discover_ucs_c_rack_server_power,
    parse_ucs_c_rack_server_power,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "computeMbPowerStats",
                    "dn sys/rack-unit-1/board/power-stats",
                    "consumedPower 88",
                    "inputCurrent 6.00",
                    "inputVoltage 12.100",
                ],
                [
                    "computeMbPowerStats",
                    "dn sys/rack-unit-2/board/power-stats",
                    "consumedPower 90",
                    "inputCurrent 7.00",
                    "inputVoltage 12.100",
                ],
            ],
            [("Rack Unit 1", {}), ("Rack Unit 2", {})],
        ),
    ],
)
def test_discover_ucs_c_rack_server_power(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_c_rack_server_power check."""
    parsed = parse_ucs_c_rack_server_power(string_table)
    result = list(discover_ucs_c_rack_server_power(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Rack Unit 1",
            {"power_upper_levels": (90, 100)},
            [
                [
                    "computeMbPowerStats",
                    "dn sys/rack-unit-1/board/power-stats",
                    "consumedPower 88",
                    "inputCurrent 6.00",
                    "inputVoltage 12.100",
                ],
                [
                    "computeMbPowerStats",
                    "dn sys/rack-unit-2/board/power-stats",
                    "consumedPower 90",
                    "inputCurrent 7.00",
                    "inputVoltage 12.100",
                ],
            ],
            [
                (0, "Power: 88.00 W", [("power", 88.0, 90, 100)]),
                (0, "Current: 6.0 A"),
                (0, "Voltage: 12.1 V"),
            ],
        ),
        (
            "Rack Unit 2",
            {"power_upper_levels": (90, 100)},
            [
                [
                    "computeMbPowerStats",
                    "dn sys/rack-unit-1/board/power-stats",
                    "consumedPower 88",
                    "inputCurrent 6.00",
                    "inputVoltage 12.100",
                ],
                [
                    "computeMbPowerStats",
                    "dn sys/rack-unit-2/board/power-stats",
                    "consumedPower 90",
                    "inputCurrent 7.00",
                    "inputVoltage 12.100",
                ],
            ],
            [
                (1, "Power: 90.00 W (warn/crit at 90.00 W/100.00 W)", [("power", 90.0, 90, 100)]),
                (0, "Current: 7.0 A"),
                (0, "Voltage: 12.1 V"),
            ],
        ),
    ],
)
def test_check_ucs_c_rack_server_power(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_c_rack_server_power check."""
    parsed = parse_ucs_c_rack_server_power(string_table)
    result = list(check_ucs_c_rack_server_power(item, params, parsed))
    assert result == expected_results
