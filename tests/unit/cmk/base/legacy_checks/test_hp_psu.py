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
from cmk.base.legacy_checks.hp_psu import check_hp_psu, discover_hp_psu, parse_hp_psu


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "3", "25"], ["2", "3", "23"]], [("1", None), ("2", None)]),
    ],
)
def test_discover_hp_psu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hp_psu check."""
    parsed = parse_hp_psu(string_table)
    result = list(discover_hp_psu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        ("1", {}, [["1", "3", "25"], ["2", "3", "23"]], [0, "Powered"]),
        ("2", {}, [["1", "3", "25"], ["2", "3", "23"]], [0, "Powered"]),
    ],
)
def test_check_hp_psu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hp_psu check."""
    parsed = parse_hp_psu(string_table)
    result = list(check_hp_psu(item, params, parsed))
    assert result == expected_results
