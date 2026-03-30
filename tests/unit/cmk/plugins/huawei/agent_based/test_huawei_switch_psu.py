#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.huawei.agent_based.huawei_switch_psu import (
    check_huawei_switch_psu,
    discover_huawei_switch_psu,
    parse_huawei_switch_psu,
)

STRING_TABLE: list[StringTable] = [
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
]


def test_discover_huawei_switch_psu() -> None:
    parsed = parse_huawei_switch_psu(STRING_TABLE)
    result = sorted(s.item or "" for s in discover_huawei_switch_psu(parsed))
    assert result == ["1/1", "1/2", "2/1", "2/2", "3/1"]


@pytest.mark.parametrize(
    "item, expected_state, expected_summary",
    [
        ("1/1", State.OK, "State: enabled"),
        ("1/2", State.CRIT, "State: disabled"),
        ("2/1", State.CRIT, "State: unknown (7)"),
        ("3/1", State.OK, "State: enabled"),
    ],
)
def test_check_huawei_switch_psu(
    item: str,
    expected_state: State,
    expected_summary: str,
) -> None:
    parsed = parse_huawei_switch_psu(STRING_TABLE)
    results = list(check_huawei_switch_psu(item, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    assert len(result_objs) == 1
    assert result_objs[0].state == expected_state
    assert result_objs[0].summary == expected_summary


def test_check_huawei_switch_psu_missing_value() -> None:
    parsed = parse_huawei_switch_psu(STRING_TABLE)
    results = list(check_huawei_switch_psu("2/2", parsed))
    assert results == []
