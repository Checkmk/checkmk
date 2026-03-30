#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.legacy_checks.huawei_switch_stack import (
    check_huawei_switch_stack,
    discover_huawei_switch_stack,
    HuaweiSwitchStackParams,
    parse_huawei_switch_stack,
)

STRING_TABLE: list[StringTable] = [
    [["1"]],
    [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]],
]


def test_discover_huawei_switch_stack() -> None:
    parsed = parse_huawei_switch_stack(STRING_TABLE)
    result = {s.item: s.parameters for s in discover_huawei_switch_stack(parsed)}
    assert result == {
        "1": {"expected_role": "master"},
        "2": {"expected_role": "slave"},
        "3": {"expected_role": "standby"},
        "4": {"expected_role": "standby"},
        "5": {"expected_role": "unknown"},
    }


@pytest.mark.parametrize(
    "item, params, expected_state, expected_summary",
    [
        ("1", {"expected_role": "master"}, State.OK, "master"),
        ("2", {"expected_role": "slave"}, State.OK, "slave"),
        ("3", {"expected_role": "standby"}, State.OK, "standby"),
        ("4", {"expected_role": "slave"}, State.CRIT, "Unexpected role: standby (Expected: slave)"),
        ("5", {"expected_role": "unknown"}, State.CRIT, "unknown"),
    ],
)
def test_check_huawei_switch_stack(
    item: str,
    params: HuaweiSwitchStackParams,
    expected_state: State,
    expected_summary: str,
) -> None:
    parsed = parse_huawei_switch_stack(STRING_TABLE)
    results = list(check_huawei_switch_stack(item, params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    assert len(result_objs) == 1
    assert result_objs[0].state == expected_state
    assert result_objs[0].summary == expected_summary
