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
from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_temp
from cmk.base.legacy_checks.dell_poweredge_temp import (
    discover_dell_poweredge_temp,
    parse_dell_poweredge_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["1", "1", "2", "3", "170", "System Board Inlet Temp", "470", "420", "30", "-70"],
                ["1", "2", "2", "3", "300", "System Board Exhaust Temp", "750", "700", "80", "30"],
                ["1", "3", "1", "2", "", "CPU1 Temp", "", "", "", ""],
                ["1", "4", "1", "2", "", "CPU2 Temp", "", "", "", ""],
            ],
            [("System Board Exhaust", {}), ("System Board Inlet", {})],
        ),
    ],
)
def test_discover_dell_poweredge_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for dell_poweredge_temp check."""
    parsed = parse_dell_poweredge_temp(string_table)
    result = list(discover_dell_poweredge_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "System Board Exhaust",
            {},
            [
                ["1", "1", "2", "3", "170", "System Board Inlet Temp", "470", "420", "30", "-70"],
                ["1", "2", "2", "3", "300", "System Board Exhaust Temp", "750", "700", "80", "30"],
                ["1", "3", "1", "2", "", "CPU1 Temp", "", "", "", ""],
                ["1", "4", "1", "2", "", "CPU2 Temp", "", "", "", ""],
            ],
            [(0, "30.0 °C", [("temp", 30.0, 70.0, 75.0)])],
        ),
        (
            "System Board Inlet",
            {},
            [
                ["1", "1", "2", "3", "170", "System Board Inlet Temp", "470", "420", "30", "-70"],
                ["1", "2", "2", "3", "300", "System Board Exhaust Temp", "750", "700", "80", "30"],
                ["1", "3", "1", "2", "", "CPU1 Temp", "", "", "", ""],
                ["1", "4", "1", "2", "", "CPU2 Temp", "", "", "", ""],
            ],
            [(0, "17.0 °C", [("temp", 17.0, 42.0, 47.0)])],
        ),
    ],
)
def test_check_dell_poweredge_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for dell_poweredge_temp check."""
    parsed = parse_dell_poweredge_temp(string_table)
    result = list(check_dell_poweredge_temp(item, params, parsed))
    assert result == expected_results
