#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.huawei_switch_fan import (
    check_huawei_switch_fan,
    inventory_huawei_switch_fan,
    parse_huawei_switch_fan,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["1.1", "50", "1"], ["1.2", "80", "1"], ["2.5", "50", "0"], ["2.7", "90", "1"]],
            [("1/1", {}), ("1/2", {}), ("2/2", {})],
        ),
    ],
)
def test_inventory_huawei_switch_fan(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for huawei_switch_fan check."""
    parsed = parse_huawei_switch_fan(string_table)
    result = list(inventory_huawei_switch_fan(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1/1",
            {},
            [["1.1", "50", "1"], ["1.2", "80", "1"], ["2.5", "50", "0"], ["2.7", "90", "1"]],
            [(0, "50.00%", [("fan_perc", 50.0, None, None)])],
        ),
        (
            "1/2",
            {"levels": (70.0, 85.0)},
            [["1.1", "50", "1"], ["1.2", "80", "1"], ["2.5", "50", "0"], ["2.7", "90", "1"]],
            [(1, "80.00% (warn/crit at 70.00%/85.00%)", [("fan_perc", 80.0, 70.0, 85.0)])],
        ),
    ],
)
def test_check_huawei_switch_fan(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for huawei_switch_fan check."""
    parsed = parse_huawei_switch_fan(string_table)
    result = list(check_huawei_switch_fan(item, params, parsed))
    assert result == expected_results
