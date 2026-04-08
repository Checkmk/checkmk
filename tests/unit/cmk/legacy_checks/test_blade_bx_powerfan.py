#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.blade_bx_powerfan import (
    check_blade_bx_powerfan,
    discover_blade_bx_powerfan,
    parse_blade_bx_powerfan,
)

STRING_TABLE_1 = [
    ["3", "Fan-1", "500", "1000", "6400", "2"],
    ["3", "Fan-2", "250", "1000", "5248", "2"],
    ["3", "Fan-3", "900", "1000", "5248", "2"],
    ["8", "Fan-4", "500", "1000", "5248", "2"],  # status=not-present
    ["4", "Fan-5", "500", "1000", "5248", "2"],  # status=fail
    ["1", "Fan-6", "500", "1000", "5248", "0"],  # ctrlstate
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                ("Fan-1", {}),
                ("Fan-2", {}),
                ("Fan-3", {}),
                ("Fan-5", {}),
                ("Fan-6", {}),
            ],
        ),
    ],
)
def test_discover_blade_bx_powerfan(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, object]]]
) -> None:
    parsed = parse_blade_bx_powerfan(string_table)
    result = list(discover_blade_bx_powerfan(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            {
                "Fan-1": (
                    0,
                    "Speed at 500 RPM, 50.0% of max",
                    [("perc", 50.0, 30, 20, "0", "100"), ("rpm", "500")],
                ),
                "Fan-2": (
                    1,
                    "Speed at 250 RPM, 25.0% of max (warn/crit below 30.0%/20.0%)",
                    [("perc", 25.0, 30, 20, "0", "100"), ("rpm", "250")],
                ),
                "Fan-3": (
                    2,
                    "Speed at 900 RPM, 90.0% of max (warn/crit at 80.0%/90.0%)",
                    [("perc", 90.0, 30, 20, "0", "100"), ("rpm", "900")],
                ),
                "Fan-5": (
                    2,
                    "Status: fail",
                    [("perc", 50.0, 30, 20, "0", "100"), ("rpm", "500")],
                ),
                "Fan-6": (
                    2,
                    "Fan not present or poweroff",
                    [("perc", 50.0, 30, 20, "0", "100"), ("rpm", "500")],
                ),
            },
        ),
    ],
)
def test_check_blade_bx_powerfan(
    string_table: StringTable, expected_results: dict[str, list[object]]
) -> None:
    parsed = parse_blade_bx_powerfan(string_table)
    params = {"levels": (80, 90), "levels_lower": (30, 20)}
    result = {
        item_name: check_blade_bx_powerfan(item_name, params, parsed)
        for item_name, _params in discover_blade_bx_powerfan(parsed)
    }
    assert result == expected_results
