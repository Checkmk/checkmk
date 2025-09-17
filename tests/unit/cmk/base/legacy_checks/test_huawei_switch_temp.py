#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.check_legacy_includes.temperature import TempParamType
from cmk.base.legacy_checks.huawei_switch_temp import (
    check_huawei_switch_temp,
    discover_huawei_switch_temp,
    parse_huawei_switch_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    ["67108867", "HUAWEI S6720 Routing Switch"],
                    ["67108869", "Board slot 0"],
                    ["68157445", "Board slot 1"],
                    ["68157449", "MPU Board 1"],
                    ["68173836", "Card slot 1/1"],
                    ["68190220", "Card slot 1/2"],
                    ["68239373", "POWER Card 1/PWR1"],
                    ["68255757", "POWER Card 1/PWR2"],
                    ["68272141", "FAN Card 1/FAN1"],
                    ["69206021", "Board slot 2"],
                    ["69222412", "Card slot 2/1"],
                    ["69206025", "MPU Board 2"],
                    ["69206045", "MPU Board 3"],
                    ["69206055", "MPU Board 4"],
                ],
                [
                    ["67108867", "0"],
                    ["67108869", "0"],
                    ["68157445", "0"],
                    ["68157449", "40"],
                    ["68173836", "0"],
                    ["68190220", "0"],
                    ["68239373", "0"],
                    ["68255757", "0"],
                    ["68272141", "0"],
                    ["69206021", "0"],
                    ["69222412", "0"],
                    ["69206025", "85"],
                    ["69206045", "95"],
                ],
            ],
            [("1", {}), ("2", {}), ("3", {}), ("4", {})],
        ),
    ],
)
def test_discover_huawei_switch_temp(
    string_table: list[StringTable], expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for huawei_switch_temp check."""
    parsed = parse_huawei_switch_temp(string_table)
    result = list(discover_huawei_switch_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {"levels": (80.0, 90.0)},
            [
                [
                    ["67108867", "HUAWEI S6720 Routing Switch"],
                    ["67108869", "Board slot 0"],
                    ["68157445", "Board slot 1"],
                    ["68157449", "MPU Board 1"],
                    ["68173836", "Card slot 1/1"],
                    ["68190220", "Card slot 1/2"],
                    ["68239373", "POWER Card 1/PWR1"],
                    ["68255757", "POWER Card 1/PWR2"],
                    ["68272141", "FAN Card 1/FAN1"],
                    ["69206021", "Board slot 2"],
                    ["69222412", "Card slot 2/1"],
                    ["69206025", "MPU Board 2"],
                    ["69206045", "MPU Board 3"],
                    ["69206055", "MPU Board 4"],
                ],
                [
                    ["67108867", "0"],
                    ["67108869", "0"],
                    ["68157445", "0"],
                    ["68157449", "40"],
                    ["68173836", "0"],
                    ["68190220", "0"],
                    ["68239373", "0"],
                    ["68255757", "0"],
                    ["68272141", "0"],
                    ["69206021", "0"],
                    ["69222412", "0"],
                    ["69206025", "85"],
                    ["69206045", "95"],
                ],
            ],
            [(0, "40.0 °C", [("temp", 40.0, 80.0, 90.0)])],
        ),
        (
            "2",
            {"levels": (80.0, 90.0)},
            [
                [
                    ["67108867", "HUAWEI S6720 Routing Switch"],
                    ["67108869", "Board slot 0"],
                    ["68157445", "Board slot 1"],
                    ["68157449", "MPU Board 1"],
                    ["68173836", "Card slot 1/1"],
                    ["68190220", "Card slot 1/2"],
                    ["68239373", "POWER Card 1/PWR1"],
                    ["68255757", "POWER Card 1/PWR2"],
                    ["68272141", "FAN Card 1/FAN1"],
                    ["69206021", "Board slot 2"],
                    ["69222412", "Card slot 2/1"],
                    ["69206025", "MPU Board 2"],
                    ["69206045", "MPU Board 3"],
                    ["69206055", "MPU Board 4"],
                ],
                [
                    ["67108867", "0"],
                    ["67108869", "0"],
                    ["68157445", "0"],
                    ["68157449", "40"],
                    ["68173836", "0"],
                    ["68190220", "0"],
                    ["68239373", "0"],
                    ["68255757", "0"],
                    ["68272141", "0"],
                    ["69206021", "0"],
                    ["69222412", "0"],
                    ["69206025", "85"],
                    ["69206045", "95"],
                ],
            ],
            [(1, "85.0 °C (warn/crit at 80.0/90.0 °C)", [("temp", 85.0, 80.0, 90.0)])],
        ),
        (
            "3",
            {"levels": (80.0, 90.0)},
            [
                [
                    ["67108867", "HUAWEI S6720 Routing Switch"],
                    ["67108869", "Board slot 0"],
                    ["68157445", "Board slot 1"],
                    ["68157449", "MPU Board 1"],
                    ["68173836", "Card slot 1/1"],
                    ["68190220", "Card slot 1/2"],
                    ["68239373", "POWER Card 1/PWR1"],
                    ["68255757", "POWER Card 1/PWR2"],
                    ["68272141", "FAN Card 1/FAN1"],
                    ["69206021", "Board slot 2"],
                    ["69222412", "Card slot 2/1"],
                    ["69206025", "MPU Board 2"],
                    ["69206045", "MPU Board 3"],
                    ["69206055", "MPU Board 4"],
                ],
                [
                    ["67108867", "0"],
                    ["67108869", "0"],
                    ["68157445", "0"],
                    ["68157449", "40"],
                    ["68173836", "0"],
                    ["68190220", "0"],
                    ["68239373", "0"],
                    ["68255757", "0"],
                    ["68272141", "0"],
                    ["69206021", "0"],
                    ["69222412", "0"],
                    ["69206025", "85"],
                    ["69206045", "95"],
                ],
            ],
            [(2, "95.0 °C (warn/crit at 80.0/90.0 °C)", [("temp", 95.0, 80.0, 90.0)])],
        ),
        (
            "4",
            {"levels": (80.0, 90.0)},
            [
                [
                    ["67108867", "HUAWEI S6720 Routing Switch"],
                    ["67108869", "Board slot 0"],
                    ["68157445", "Board slot 1"],
                    ["68157449", "MPU Board 1"],
                    ["68173836", "Card slot 1/1"],
                    ["68190220", "Card slot 1/2"],
                    ["68239373", "POWER Card 1/PWR1"],
                    ["68255757", "POWER Card 1/PWR2"],
                    ["68272141", "FAN Card 1/FAN1"],
                    ["69206021", "Board slot 2"],
                    ["69222412", "Card slot 2/1"],
                    ["69206025", "MPU Board 2"],
                    ["69206045", "MPU Board 3"],
                    ["69206055", "MPU Board 4"],
                ],
                [
                    ["67108867", "0"],
                    ["67108869", "0"],
                    ["68157445", "0"],
                    ["68157449", "40"],
                    ["68173836", "0"],
                    ["68190220", "0"],
                    ["68239373", "0"],
                    ["68255757", "0"],
                    ["68272141", "0"],
                    ["69206021", "0"],
                    ["69222412", "0"],
                    ["69206025", "85"],
                    ["69206045", "95"],
                ],
            ],
            [],
        ),
    ],
)
def test_check_huawei_switch_temp(
    item: str,
    params: TempParamType,
    string_table: list[StringTable],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for huawei_switch_temp check."""
    parsed = parse_huawei_switch_temp(string_table)
    result = list(check_huawei_switch_temp(item, params, parsed))
    assert result == expected_results
