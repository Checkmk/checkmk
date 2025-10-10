#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.vutlan_ems_temp import (
    check_vutlan_ems_temp,
    discover_vutlan_ems_temp,
    parse_vutlan_ems_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    ["101001", "Dry-1", "0"],
                    ["101002", "Dry-2", "0"],
                    ["101003", "Dry-3", "0"],
                    ["101004", "Dry-4", "0"],
                    ["106001", "Analog-5", "0"],
                    ["107001", "Analog-6", "0"],
                    ["201001", "Onboard Temperature", "32.80"],
                    ["201002", "Analog-1", "22.00"],
                    ["201003", "Analog-2", "22.10"],
                    ["202001", "Analog-3", "46.20"],
                    ["202002", "Analog-4", "42.10"],
                    ["203001", "Onboard Voltage DC", "12.06"],
                    ["301001", "Analog Power", "on"],
                    ["304001", "Power-1", "off"],
                    ["304002", "Power-2", "off"],
                    ["403001", "USB Web camera", "0"],
                ]
            ],
            [("Analog-1", {}), ("Analog-2", {}), ("Onboard Temperature", {})],
        ),
    ],
)
def test_discover_vutlan_ems_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for vutlan_ems_temp check."""
    parsed = parse_vutlan_ems_temp(string_table)
    result = list(discover_vutlan_ems_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Analog-1",
            {"levels": (80.0, 90.0)},
            [
                [
                    ["101001", "Dry-1", "0"],
                    ["101002", "Dry-2", "0"],
                    ["101003", "Dry-3", "0"],
                    ["101004", "Dry-4", "0"],
                    ["106001", "Analog-5", "0"],
                    ["107001", "Analog-6", "0"],
                    ["201001", "Onboard Temperature", "32.80"],
                    ["201002", "Analog-1", "22.00"],
                    ["201003", "Analog-2", "22.10"],
                    ["202001", "Analog-3", "46.20"],
                    ["202002", "Analog-4", "42.10"],
                    ["203001", "Onboard Voltage DC", "12.06"],
                    ["301001", "Analog Power", "on"],
                    ["304001", "Power-1", "off"],
                    ["304002", "Power-2", "off"],
                    ["403001", "USB Web camera", "0"],
                ]
            ],
            [(0, "22.0 °C", [("temp", 22.0, 80.0, 90.0)])],
        ),
        (
            "Analog-2",
            {"levels": (10.0, 20.0)},
            [
                [
                    ["101001", "Dry-1", "0"],
                    ["101002", "Dry-2", "0"],
                    ["101003", "Dry-3", "0"],
                    ["101004", "Dry-4", "0"],
                    ["106001", "Analog-5", "0"],
                    ["107001", "Analog-6", "0"],
                    ["201001", "Onboard Temperature", "32.80"],
                    ["201002", "Analog-1", "22.00"],
                    ["201003", "Analog-2", "22.10"],
                    ["202001", "Analog-3", "46.20"],
                    ["202002", "Analog-4", "42.10"],
                    ["203001", "Onboard Voltage DC", "12.06"],
                    ["301001", "Analog Power", "on"],
                    ["304001", "Power-1", "off"],
                    ["304002", "Power-2", "off"],
                    ["403001", "USB Web camera", "0"],
                ]
            ],
            [(2, "22.1 °C (warn/crit at 10.0/20.0 °C)", [("temp", 22.1, 10.0, 20.0)])],
        ),
        (
            "Onboard Temperature",
            {"levels": (80.0, 90.0)},
            [
                [
                    ["101001", "Dry-1", "0"],
                    ["101002", "Dry-2", "0"],
                    ["101003", "Dry-3", "0"],
                    ["101004", "Dry-4", "0"],
                    ["106001", "Analog-5", "0"],
                    ["107001", "Analog-6", "0"],
                    ["201001", "Onboard Temperature", "32.80"],
                    ["201002", "Analog-1", "22.00"],
                    ["201003", "Analog-2", "22.10"],
                    ["202001", "Analog-3", "46.20"],
                    ["202002", "Analog-4", "42.10"],
                    ["203001", "Onboard Voltage DC", "12.06"],
                    ["301001", "Analog Power", "on"],
                    ["304001", "Power-1", "off"],
                    ["304002", "Power-2", "off"],
                    ["403001", "USB Web camera", "0"],
                ]
            ],
            [(0, "32.8 °C", [("temp", 32.8, 80.0, 90.0)])],
        ),
    ],
)
def test_check_vutlan_ems_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for vutlan_ems_temp check."""
    parsed = parse_vutlan_ems_temp(string_table)
    result = list(check_vutlan_ems_temp(item, params, parsed))
    assert result == expected_results
