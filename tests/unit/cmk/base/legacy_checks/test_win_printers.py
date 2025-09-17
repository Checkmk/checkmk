#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.win_printers import (
    check_win_printers,
    discover_win_printers,
    parse_win_printers,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["PrinterStockholm", "3", "4", "0"],
                ["Printer", "Berlin", "3", "4", "0"],
                ["WH1_BC_O3_UPS", "0", "3", "8"],
                [
                    '"printerstatus","detectederrorstate"',
                    "-Type",
                    "OnlyIfInBoth",
                    "|",
                    "format-table",
                    "-HideTableHeaders",
                ],
            ],
            [("PrinterStockholm", {}), ("Printer Berlin", {}), ("WH1_BC_O3_UPS", {})],
        ),
    ],
)
def test_discover_win_printers(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for win_printers check."""
    parsed = parse_win_printers(string_table)
    result = list(discover_win_printers(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "PrinterStockholm",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            [
                ["PrinterStockholm", "3", "4", "0"],
                ["Printer", "Berlin", "3", "4", "0"],
                ["WH1_BC_O3_UPS", "0", "3", "8"],
                [
                    '"printerstatus","detectederrorstate"',
                    "-Type",
                    "OnlyIfInBoth",
                    "|",
                    "format-table",
                    "-HideTableHeaders",
                ],
            ],
            [(0, "Current jobs: 3", []), (0, "State: Printing")],
        ),
        (
            "Printer Berlin",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            [
                ["PrinterStockholm", "3", "4", "0"],
                ["Printer", "Berlin", "3", "4", "0"],
                ["WH1_BC_O3_UPS", "0", "3", "8"],
                [
                    '"printerstatus","detectederrorstate"',
                    "-Type",
                    "OnlyIfInBoth",
                    "|",
                    "format-table",
                    "-HideTableHeaders",
                ],
            ],
            [(0, "Current jobs: 3", []), (0, "State: Printing")],
        ),
        (
            "WH1_BC_O3_UPS",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            [
                ["PrinterStockholm", "3", "4", "0"],
                ["Printer", "Berlin", "3", "4", "0"],
                ["WH1_BC_O3_UPS", "0", "3", "8"],
                [
                    '"printerstatus","detectederrorstate"',
                    "-Type",
                    "OnlyIfInBoth",
                    "|",
                    "format-table",
                    "-HideTableHeaders",
                ],
            ],
            [(0, "Current jobs: 0", []), (0, "State: Idle"), (1, "Error state: Jammed")],
        ),
    ],
)
def test_check_win_printers(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for win_printers check."""
    parsed = parse_win_printers(string_table)
    result = list(check_win_printers(item, params, parsed))
    assert result == expected_results
