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
from cmk.base.legacy_checks.hp_fan import check_hp_fan, discover_hp_fan, parse_hp_fan


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]],
            [("2/0", None), ("3/1", None), ("4/2", None)],
        ),
    ],
)
def test_discover_hp_fan(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hp_fan check."""
    parsed = parse_hp_fan(string_table)
    result = list(discover_hp_fan(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        ("2/0", {}, [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]], (0, "ok")),
        ("3/1", {}, [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]], (1, "underspeed")),
        ("4/2", {}, [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]], (2, "removed")),
    ],
)
def test_check_hp_fan(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hp_fan check."""
    parsed = parse_hp_fan(string_table)
    result = check_hp_fan(item, params, parsed)
    assert result == expected_results
