#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.printer.agent_based.win_printers import (
    check_win_printers,
    discover_win_printers,
    parse_win_printers,
)

_STRING_TABLE: list[list[str]] = [
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
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            [
                Service(item="PrinterStockholm"),
                Service(item="Printer Berlin"),
                Service(item="WH1_BC_O3_UPS"),
            ],
        ),
    ],
)
def test_discover_win_printers(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_win_printers(string_table)
    result = list(discover_win_printers(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "PrinterStockholm",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Current jobs: 3"),
                Result(state=State.OK, summary="State: Printing"),
            ],
        ),
        (
            "Printer Berlin",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Current jobs: 3"),
                Result(state=State.OK, summary="State: Printing"),
            ],
        ),
        (
            "WH1_BC_O3_UPS",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Current jobs: 0"),
                Result(state=State.OK, summary="State: Idle"),
                Result(state=State.WARN, summary="Error state: Jammed"),
            ],
        ),
    ],
)
def test_check_win_printers(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Result],
) -> None:
    parsed = parse_win_printers(string_table)
    result = list(check_win_printers(item, params, parsed))
    assert result == expected_results
