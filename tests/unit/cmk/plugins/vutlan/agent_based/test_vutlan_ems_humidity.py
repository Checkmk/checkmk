#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.vutlan.agent_based import vutlan_ems_humidity

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
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (STRING_TABLE, [Service(item="Analog-3"), Service(item="Analog-4")]),
    ],
)
def test_discover_vutlan_ems_humidity(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    section = vutlan_ems_humidity.parse_vutlan_ems_humidity(string_table)
    result = list(vutlan_ems_humidity.discover_vutlan_ems_humidity(section))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Analog-3",
            {"levels": (15.0, 16.0)},
            STRING_TABLE,
            [
                Result(state=State.CRIT, summary="46.20% (warn/crit at 15.00%/16.00%)"),
                Metric("humidity", 46.2, levels=(15.0, 16.0), boundaries=(0.0, 100.0)),
            ],
        ),
        (
            "Analog-4",
            {"levels": (50.0, 60.0)},
            STRING_TABLE,
            [
                Result(state=State.OK, summary="42.10%"),
                Metric("humidity", 42.1, levels=(50.0, 60.0), boundaries=(0.0, 100.0)),
            ],
        ),
    ],
)
def test_check_vutlan_ems_humidity(
    item: str,
    params: Mapping[str, object],
    string_table: StringTable,
    expected_results: Sequence[object],
) -> None:
    section = vutlan_ems_humidity.parse_vutlan_ems_humidity(string_table)
    result = list(vutlan_ems_humidity.check_vutlan_ems_humidity(item, params, section))
    assert result == expected_results
