#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.blade_bx_temp import (
    check_blade_bx_temp,
    discover_blade_bx_temp,
    parse_blade_bx_temp,
)

STRING_TABLE_1 = [
    # _index, status, descr, level_warn, level_crit, temp, crit_react
    ["1", "3", "Descr1", "70", "85", "32", "2"],
    ["2", "3", "Descr2", "70", "85", "75", "2"],
    ["3", "3", "Descr3", "70", "85", "90", "2"],
    ["4", "7", "Descr4", "70", "85", "32", "2"],  # status: not available
    ["5", "4", "Descr5", "70", "85", "32", "2"],  # status: sensor-faild
    ["6", "3", "Descr6", "70", "85", "32", "1"],  # crit_react != 2
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                ("Descr1", None),
                ("Descr2", None),
                ("Descr3", None),
                ("Descr5", None),
                ("Descr6", None),
            ],
        ),
    ],
)
def test_discover_blade_bx_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, object]]]
) -> None:
    parsed = parse_blade_bx_temp(string_table)
    result = list(discover_blade_bx_temp(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "params", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            None,
            {
                "Descr1": [0, "32 °C", [("temp", 32, 70, 85)]],
                "Descr2": [1, "75 °C (device warn/crit at 70/85 °C)", [("temp", 75, 70, 85)]],
                "Descr3": [2, "90 °C (device warn/crit at 70/85 °C)", [("temp", 90, 70, 85)]],
                "Descr5": [2, "Status is sensor-faild", [("temp", 32, 70, 85)]],
                "Descr6": [2, "Temperature not present or poweroff", [("temp", 32, 70, 85)]],
            },
            id="01_no_params",
        ),
        pytest.param(
            STRING_TABLE_1,
            {"levels": (60, 70)},
            {
                "Descr1": [0, "32 °C", [("temp", 32, 60, 70)]],
                "Descr2": [2, "75 °C (warn/crit at 60/70 °C)", [("temp", 75, 60, 70)]],
                "Descr3": [2, "90 °C (warn/crit at 60/70 °C)", [("temp", 90, 60, 70)]],
                "Descr5": [2, "Status is sensor-faild", [("temp", 32, 60, 70)]],
                "Descr6": [2, "Temperature not present or poweroff", [("temp", 32, 60, 70)]],
            },
            id="02_with_levels",
        ),
        pytest.param(
            STRING_TABLE_1,
            {"levels_lower": (40, 30)},
            {
                "Descr1": [
                    1,
                    "32 °C (warn/crit below 40/30 °C) (device warn/crit at 70/85 °C)",
                    [("temp", 32, 70, 85)],
                ],
                "Descr2": [
                    1,
                    "75 °C (warn/crit below 40/30 °C) (device warn/crit at 70/85 °C)",
                    [("temp", 75, 70, 85)],
                ],
                "Descr3": [
                    2,
                    "90 °C (warn/crit below 40/30 °C) (device warn/crit at 70/85 °C)",
                    [("temp", 90, 70, 85)],
                ],
                "Descr5": [2, "Status is sensor-faild", [("temp", 32, 70, 85)]],
                "Descr6": [2, "Temperature not present or poweroff", [("temp", 32, 70, 85)]],
            },
            id="03_with_levels_lower",
        ),
    ],
)
def test_check_blade_bx_temp(
    string_table: StringTable,
    params: None | Mapping[str, tuple[float, float]],
    expected_results: dict[str, list[object]],
) -> None:
    parsed = parse_blade_bx_temp(string_table)
    result = {
        item_name: list(check_blade_bx_temp(item_name, params, parsed))
        for item_name, _params in discover_blade_bx_temp(parsed)
    }
    assert result == expected_results
