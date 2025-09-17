#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.huawei_switch_psu import (
    check_huawei_switch_psu,
    discover_huawei_switch_psu,
    parse_huawei_switch_psu,
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
                    ["69206035", "POWER Card 2/PWR1"],
                    ["69206038", "POWER Card 2/PWR2"],
                    ["69206045", "MPU Board 3"],
                    ["69206048", "POWER Card 3/PWR1"],
                ],
                [
                    ["67108867", "3"],
                    ["67108869", "3"],
                    ["68157445", "3"],
                    ["68157449", "3"],
                    ["68173836", "3"],
                    ["68190220", "3"],
                    ["68239373", "3"],
                    ["68255757", "2"],
                    ["68272141", "3"],
                    ["69206021", "3"],
                    ["69222412", "3"],
                    ["69206025", "3"],
                    ["69206035", "7"],
                    ["69206045", "3"],
                    ["69206048", "3"],
                ],
            ],
            [("1/1", {}), ("1/2", {}), ("2/1", {}), ("2/2", {}), ("3/1", {})],
        ),
    ],
)
def test_discover_huawei_switch_psu(
    string_table: list[StringTable], expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for huawei_switch_psu check."""
    parsed = parse_huawei_switch_psu(string_table)
    result = list(discover_huawei_switch_psu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1/1",
            {},
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
                    ["69206035", "POWER Card 2/PWR1"],
                    ["69206038", "POWER Card 2/PWR2"],
                    ["69206045", "MPU Board 3"],
                    ["69206048", "POWER Card 3/PWR1"],
                ],
                [
                    ["67108867", "3"],
                    ["67108869", "3"],
                    ["68157445", "3"],
                    ["68157449", "3"],
                    ["68173836", "3"],
                    ["68190220", "3"],
                    ["68239373", "3"],
                    ["68255757", "2"],
                    ["68272141", "3"],
                    ["69206021", "3"],
                    ["69222412", "3"],
                    ["69206025", "3"],
                    ["69206035", "7"],
                    ["69206045", "3"],
                    ["69206048", "3"],
                ],
            ],
            [(0, "State: enabled")],
        ),
        (
            "1/2",
            {},
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
                    ["69206035", "POWER Card 2/PWR1"],
                    ["69206038", "POWER Card 2/PWR2"],
                    ["69206045", "MPU Board 3"],
                    ["69206048", "POWER Card 3/PWR1"],
                ],
                [
                    ["67108867", "3"],
                    ["67108869", "3"],
                    ["68157445", "3"],
                    ["68157449", "3"],
                    ["68173836", "3"],
                    ["68190220", "3"],
                    ["68239373", "3"],
                    ["68255757", "2"],
                    ["68272141", "3"],
                    ["69206021", "3"],
                    ["69222412", "3"],
                    ["69206025", "3"],
                    ["69206035", "7"],
                    ["69206045", "3"],
                    ["69206048", "3"],
                ],
            ],
            [(2, "State: disabled")],
        ),
        (
            "2/1",
            {},
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
                    ["69206035", "POWER Card 2/PWR1"],
                    ["69206038", "POWER Card 2/PWR2"],
                    ["69206045", "MPU Board 3"],
                    ["69206048", "POWER Card 3/PWR1"],
                ],
                [
                    ["67108867", "3"],
                    ["67108869", "3"],
                    ["68157445", "3"],
                    ["68157449", "3"],
                    ["68173836", "3"],
                    ["68190220", "3"],
                    ["68239373", "3"],
                    ["68255757", "2"],
                    ["68272141", "3"],
                    ["69206021", "3"],
                    ["69222412", "3"],
                    ["69206025", "3"],
                    ["69206035", "7"],
                    ["69206045", "3"],
                    ["69206048", "3"],
                ],
            ],
            [(2, "State: unknown (7)")],
        ),
        (
            "2/2",
            {},
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
                    ["69206035", "POWER Card 2/PWR1"],
                    ["69206038", "POWER Card 2/PWR2"],
                    ["69206045", "MPU Board 3"],
                    ["69206048", "POWER Card 3/PWR1"],
                ],
                [
                    ["67108867", "3"],
                    ["67108869", "3"],
                    ["68157445", "3"],
                    ["68157449", "3"],
                    ["68173836", "3"],
                    ["68190220", "3"],
                    ["68239373", "3"],
                    ["68255757", "2"],
                    ["68272141", "3"],
                    ["69206021", "3"],
                    ["69222412", "3"],
                    ["69206025", "3"],
                    ["69206035", "7"],
                    ["69206045", "3"],
                    ["69206048", "3"],
                ],
            ],
            [],
        ),
        (
            "3/1",
            {},
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
                    ["69206035", "POWER Card 2/PWR1"],
                    ["69206038", "POWER Card 2/PWR2"],
                    ["69206045", "MPU Board 3"],
                    ["69206048", "POWER Card 3/PWR1"],
                ],
                [
                    ["67108867", "3"],
                    ["67108869", "3"],
                    ["68157445", "3"],
                    ["68157449", "3"],
                    ["68173836", "3"],
                    ["68190220", "3"],
                    ["68239373", "3"],
                    ["68255757", "2"],
                    ["68272141", "3"],
                    ["69206021", "3"],
                    ["69222412", "3"],
                    ["69206025", "3"],
                    ["69206035", "7"],
                    ["69206045", "3"],
                    ["69206048", "3"],
                ],
            ],
            [(0, "State: enabled")],
        ),
    ],
)
def test_check_huawei_switch_psu(
    item: str,
    params: Mapping[str, Any],
    string_table: list[StringTable],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for huawei_switch_psu check."""
    parsed = parse_huawei_switch_psu(string_table)
    result = list(check_huawei_switch_psu(item, params, parsed))
    assert result == expected_results
