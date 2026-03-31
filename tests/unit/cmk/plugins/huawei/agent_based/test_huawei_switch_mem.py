#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.huawei.agent_based.huawei_switch_mem import (
    check_huawei_switch_mem,
    discover_huawei_switch_mem,
    parse_huawei_switch_mem,
)

STRING_TABLE: Sequence[StringTable] = [
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
]


def test_discover_huawei_switch_mem() -> None:
    """Test discovery function for huawei_switch_mem check."""
    parsed = parse_huawei_switch_mem(STRING_TABLE)
    result = list(discover_huawei_switch_mem(parsed))
    items = sorted(s.item or "" for s in result)
    assert items == ["1", "2", "3", "4"]
    assert all(isinstance(s, Service) for s in result)


@pytest.mark.parametrize(
    "item, params, expected_state, expected_summary, expected_metric_name",
    [
        (
            "1",
            {"levels": (80.0, 90.0)},
            State.OK,
            "Usage: 22.00%",
            "mem_used_percent",
        ),
        (
            "2",
            {"levels": (80.0, 90.0)},
            State.WARN,
            "Usage: 85.00% (warn/crit at 80.00%/90.00%)",
            "mem_used_percent",
        ),
        (
            "3",
            {"levels": (80.0, 90.0)},
            State.CRIT,
            "Usage: 95.00% (warn/crit at 80.00%/90.00%)",
            "mem_used_percent",
        ),
    ],
)
def test_check_huawei_switch_mem(
    item: str,
    params: Mapping[str, tuple[float, float]],
    expected_state: State,
    expected_summary: str,
    expected_metric_name: str,
) -> None:
    """Test check function for huawei_switch_mem check."""
    parsed = parse_huawei_switch_mem(STRING_TABLE)
    results = list(check_huawei_switch_mem(item, params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == expected_state
    assert result_objs[0].summary == expected_summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == expected_metric_name


def test_check_huawei_switch_mem_item_not_found() -> None:
    """Test check function returns empty for non-existent item."""
    parsed = parse_huawei_switch_mem(STRING_TABLE)
    results = list(check_huawei_switch_mem("4", {"levels": (80.0, 90.0)}, parsed))
    assert results == []
