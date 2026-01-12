#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Never

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.huawei_switch_mem import (
    check_huawei_switch_mem,
    discover_huawei_switch_mem,
    parse_huawei_switch_mem,
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
                    ["68157449", "22"],
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
def test_discover_huawei_switch_mem(
    string_table: Sequence[StringTable],
    expected_discoveries: Sequence[tuple[str, Mapping[str, Never]]],
) -> None:
    """Test discovery function for huawei_switch_mem check."""
    parsed = parse_huawei_switch_mem(string_table)
    result = list(discover_huawei_switch_mem(parsed))
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
                    ["68157449", "22"],
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
            [(0, "Usage: 22.00%", [("mem_used_percent", 22.0, 80.0, 90.0)])],
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
                    ["68157449", "22"],
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
            [
                (
                    1,
                    "Usage: 85.00% (warn/crit at 80.00%/90.00%)",
                    [("mem_used_percent", 85.0, 80.0, 90.0)],
                )
            ],
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
                    ["68157449", "22"],
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
            [
                (
                    2,
                    "Usage: 95.00% (warn/crit at 80.00%/90.00%)",
                    [("mem_used_percent", 95.0, 80.0, 90.0)],
                )
            ],
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
                    ["68157449", "22"],
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
def test_check_huawei_switch_mem(
    item: str,
    params: Mapping[str, tuple[float, float]],
    string_table: Sequence[StringTable],
    expected_results: Sequence[tuple[int, str, Sequence[tuple[str, float, float, float]]]],
) -> None:
    """Test check function for huawei_switch_mem check."""
    parsed = parse_huawei_switch_mem(string_table)
    result = list(check_huawei_switch_mem(item, params, parsed))
    assert result == expected_results
