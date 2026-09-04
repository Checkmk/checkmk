#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.vutlan_ems_leakage import (
    check_vutlan_ems_leakage,
    discover_vutlan_ems_leakage,
    parse_vutlan_ems_leakage,
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
    ["202001", "Analog-3", "46.20"],
    ["202002", "Analog-4", "42.10"],
    ["203001", "Onboard Voltage DC", "12.06"],
    ["301001", "Analog Power", "on"],
    ["304001", "Power-1", "off"],
    ["304002", "Power-2", "off"],
    ["403001", "USB Web camera", "0"],
    ["107002", "Banana", "1"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (STRING_TABLE, [Service(item="Analog-6"), Service(item="Banana")]),
    ],
)
def test_discover_vutlan_ems_leakage(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    section = parse_vutlan_ems_leakage(string_table)
    result = list(discover_vutlan_ems_leakage(section))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "Analog-6",
            STRING_TABLE,
            [Result(state=State.OK, summary="No leak detected")],
        ),
        (
            "Banana",
            STRING_TABLE,
            [Result(state=State.CRIT, summary="Leak detected")],
        ),
    ],
)
def test_check_vutlan_ems_leakage(
    item: str,
    string_table: StringTable,
    expected_results: Sequence[object],
) -> None:
    section = parse_vutlan_ems_leakage(string_table)
    result = list(check_vutlan_ems_leakage(item, section))
    assert result == expected_results
