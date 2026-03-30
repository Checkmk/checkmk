#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.huawei.agent_based.huawei_switch_fan import (
    check_huawei_switch_fan,
    discover_huawei_switch_fan,
    HuaweiFanParams,
    parse_huawei_switch_fan,
)

STRING_TABLE: StringTable = [
    ["1.1", "50", "1"],
    ["1.2", "80", "1"],
    ["2.5", "50", "0"],
    ["2.7", "90", "1"],
]


def test_discover_huawei_switch_fan() -> None:
    """Test discovery function for huawei_switch_fan check."""
    parsed = parse_huawei_switch_fan(STRING_TABLE)
    result = list(discover_huawei_switch_fan(parsed))
    items = sorted(s.item or "" for s in result)
    assert items == ["1/1", "1/2", "2/2"]
    assert all(isinstance(s, Service) for s in result)


@pytest.mark.parametrize(
    "item, params, expected_state, expected_summary, expected_metric_name",
    [
        (
            "1/1",
            {},
            State.OK,
            "50.00%",
            "fan_perc",
        ),
        (
            "1/2",
            {"levels": (70.0, 85.0)},
            State.WARN,
            "80.00% (warn/crit at 70.00%/85.00%)",
            "fan_perc",
        ),
    ],
)
def test_check_huawei_switch_fan(
    item: str,
    params: HuaweiFanParams,
    expected_state: State,
    expected_summary: str,
    expected_metric_name: str,
) -> None:
    """Test check function for huawei_switch_fan check."""
    parsed = parse_huawei_switch_fan(STRING_TABLE)
    results = list(check_huawei_switch_fan(item, params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == 1
    assert result_objs[0].state == expected_state
    assert result_objs[0].summary == expected_summary
    assert len(metric_objs) == 1
    assert metric_objs[0].name == expected_metric_name
