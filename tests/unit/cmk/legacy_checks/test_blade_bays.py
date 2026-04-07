#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.blade_bays import (
    check_blade_bays,
    discover_blade_bays,
    parse_blade_bays,
)

STRING_TABLE_1 = [
    [
        ["1", "SomeName1", "1", "type1(ignored)", "1", "4W", "6W"],
        ["2", "SomeName2", "0", "type2(ignored)", "A", "5W", "5W"],
    ],
    [
        ["1", "SomeName1", "1", "type3(ignored)", "1", "5W", "5W"],
        ["2", "SomeName3", "1", "type4(ignored)", "B", "5W", "5W"],
        ["2", "SomeName4", "x", "type5(ignored)", "2", "5W", "5W"],
    ],
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                ("PD1 SomeName1", {}),
                ("PD1 SomeName2", {}),
                ("PD2 SomeName1", {}),
                ("PD2 SomeName3", {}),
            ],
        ),
    ],
)
def test_discover_blade_bays(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, object]]]
) -> None:
    parsed = parse_blade_bays(string_table)
    result = list(discover_blade_bays(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            {
                "PD1 SomeName1": [
                    (0, "Device status: on(0)"),
                    (0, "Max. power: 6 W, Type: type1, ID: 1"),
                    (0, "Power: 4.0 W", [("power", 4, None, None)]),
                    (0, "Status: on"),
                ],
                "PD1 SomeName2": [
                    (0, "Device status: standby(0)"),
                    (0, "Max. power: 5 W, Type: type2, ID: A"),
                    (0, "Power: 5.0 W", [("power", 5, None, None)]),
                    (0, "Status: standby"),
                ],
                "PD2 SomeName1": [
                    (0, "Device status: on(0)"),
                    (0, "Max. power: 5 W, Type: type3, ID: 1"),
                    (0, "Power: 5.0 W", [("power", 5, None, None)]),
                    (0, "Status: on"),
                ],
                "PD2 SomeName3": [
                    (0, "Device status: on(0)"),
                    (0, "Max. power: 5 W, Type: type4, ID: B"),
                    (0, "Power: 5.0 W", [("power", 5, None, None)]),
                    (0, "Status: on"),
                ],
            },
        ),
    ],
)
def test_check_blade_bays(
    string_table: StringTable, expected_results: dict[str, list[object]]
) -> None:
    parsed = parse_blade_bays(string_table)
    result = {
        item_name: sorted(check_blade_bays(item_name, params, parsed))
        for item_name, params in discover_blade_bays(parsed)
    }
    assert result == expected_results
