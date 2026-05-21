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
from cmk.base.legacy_checks.dell_idrac_fans import (
    check_dell_idrac_fans,
    inventory_dell_idrac_fans,
    parse_dell_idrac_fans,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["1", "1", "", "System Board Fan1A", "", "", "", ""],
                ["2", "2", "", "System Board Fan1B", "", "", "", ""],
                ["3", "10", "", "System Board Fan2A", "", "", "", ""],
                # OK fan with only a subset of thresholds populated (upper warn + lower crit).
                # Regression for a crash caused by int("") on the empty threshold columns.
                ["4", "3", "7912", "FAN1A", "21500", "", "8000", ""],
                # OK fan with no thresholds at all — exercises the empty-params branch.
                ["5", "3", "7000", "FAN2A", "", "", "", ""],
            ],
            [("3", {}), ("4", {}), ("5", {})],
        ),
    ],
)
def test_inventory_dell_idrac_fans(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for dell_idrac_fans check."""
    parsed = parse_dell_idrac_fans(string_table)
    result = list(inventory_dell_idrac_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "3",
            {},
            [
                ["1", "1", "", "System Board Fan1A", "", "", "", ""],
                ["2", "2", "", "System Board Fan1B", "", "", "", ""],
                ["3", "10", "", "System Board Fan2A", "", "", "", ""],
            ],
            [(2, "Status: FAILED, Name: System Board Fan2A")],
        ),
        (
            "4",
            {},
            [
                # OK fan with only a subset of thresholds populated (upper warn + lower crit).
                # Regression for a crash caused by int("") on the empty threshold columns.
                ["4", "3", "7912", "FAN1A", "21500", "", "8000", ""],
            ],
            [
                (0, "Status: OK, Name: FAN1A"),
                (1, "Speed: 7912 RPM (warn/crit below 8000 RPM/never)", []),
            ],
        ),
        (
            "5",
            {},
            [
                # OK fan with no thresholds at all — exercises the empty-params branch.
                ["5", "3", "7000", "FAN2A", "", "", "", ""],
            ],
            [(0, "Status: OK, Name: FAN2A"), (0, "Speed: 7000 RPM", [])],
        ),
    ],
)
def test_check_dell_idrac_fans(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for dell_idrac_fans check."""
    parsed = parse_dell_idrac_fans(string_table)
    result = list(check_dell_idrac_fans(item, params, parsed))
    assert result == expected_results
