#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.huawei_switch_stack import (
    check_huawei_switch_stack,
    discover_huawei_switch_stack,
    parse_huawei_switch_stack,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [[["1"]], [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]]],
            [
                ("1", {"expected_role": "master"}),
                ("2", {"expected_role": "slave"}),
                ("3", {"expected_role": "standby"}),
                ("4", {"expected_role": "standby"}),
                ("5", {"expected_role": "unknown"}),
            ],
        ),
    ],
)
def test_discover_huawei_switch_stack(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for huawei_switch_stack check."""
    parsed = parse_huawei_switch_stack(string_table)
    result = list(discover_huawei_switch_stack(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {"expected_role": "master"},
            [[["1"]], [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]]],
            [(0, "master")],
        ),
        (
            "2",
            {"expected_role": "slave"},
            [[["1"]], [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]]],
            [(0, "slave")],
        ),
        (
            "3",
            {"expected_role": "standby"},
            [[["1"]], [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]]],
            [(0, "standby")],
        ),
        (
            "4",
            {"expected_role": "slave"},
            [[["1"]], [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]]],
            [(2, "Unexpected role: standby (Expected: slave)")],
        ),
        (
            "5",
            {"expected_role": "unknown"},
            [[["1"]], [["1", "1"], ["2", "3"], ["3", "2"], ["4", "2"], ["5", "4"]]],
            [(2, "unknown")],
        ),
    ],
)
def test_check_huawei_switch_stack(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for huawei_switch_stack check."""
    parsed = parse_huawei_switch_stack(string_table)
    result = list(check_huawei_switch_stack(item, params, parsed))
    assert result == expected_results
