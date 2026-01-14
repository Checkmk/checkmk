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
from cmk.base.legacy_checks.f5_bigip_chassis_temp import (
    check_f5_bigip_chassis_temp,
    discover_f5_bigip_chassis_temp,
    parse_f5_bigip_chassis_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["1", "30"], ["2", "32"], ["3", "36"], ["4", "41"], ["5", "41"]],
            [("1", {}), ("2", {}), ("3", {}), ("4", {}), ("5", {})],
        ),
    ],
)
def test_discover_f5_bigip_chassis_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for f5_bigip_chassis_temp check."""
    parsed = parse_f5_bigip_chassis_temp(string_table)
    result = list(discover_f5_bigip_chassis_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {"levels": (35.0, 40.0)},
            [["1", "30"], ["2", "32"], ["3", "36"], ["4", "41"], ["5", "41"]],
            [(0, "30 °C", [("temp", 30, 35.0, 40.0)])],
        ),
        (
            "3",
            {"levels": (35.0, 40.0)},
            [["1", "30"], ["2", "32"], ["3", "36"], ["4", "41"], ["5", "41"]],
            [(1, "36 °C (warn/crit at 35.0/40.0 °C)", [("temp", 36, 35.0, 40.0)])],
        ),
    ],
)
def test_check_f5_bigip_chassis_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for f5_bigip_chassis_temp check."""
    parsed = parse_f5_bigip_chassis_temp(string_table)
    result = check_f5_bigip_chassis_temp(item, params, parsed)
    assert result == expected_results[0]  # Compare to the first (and only) expected result
