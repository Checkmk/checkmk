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
from cmk.base.legacy_checks.fortigate_memory import (
    check_fortigate_memory,
    discover_fortigate_memory,
    parse_fortigate_memory,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["42"]], [(None, {})]),
    ],
)
def test_discover_fortigate_memory(
    string_table: StringTable, expected_discoveries: Sequence[tuple[None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for fortigate_memory check."""
    parsed = parse_fortigate_memory(string_table)
    result = list(discover_fortigate_memory(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"levels": (30.0, 80.0)},
            [["42"]],
            [(1, "Usage: 42.00% (warn/crit at 30.00%/80.00%)", [("mem_usage", 42, 30.0, 80.0)])],
        ),
        (
            None,
            {"levels": (-80, -30)},
            [["42"]],
            [
                (3, "Absolute levels are not supported"),
                (0, "Usage: 42.00%", [("mem_usage", 42, None, None)]),
            ],
        ),
    ],
)
def test_check_fortigate_memory(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for fortigate_memory check."""
    parsed = parse_fortigate_memory(string_table)
    result = list(check_fortigate_memory(item, params, parsed))
    assert result == expected_results
