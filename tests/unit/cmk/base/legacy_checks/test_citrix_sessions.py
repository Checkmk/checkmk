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
from cmk.base.legacy_checks.citrix_sessions import (
    check_citrix_sessions,
    discover_citrix_sessions,
    parse_citrix_sessions,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["sessions", "1"], ["active_sessions", "1"], ["inactive_sessions", "0"]],
            [(None, {"total": (60, 65), "active": (60, 65), "inactive": (10, 15)})],
        ),
    ],
)
def test_discover_citrix_sessions(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for citrix_sessions check."""
    parsed = parse_citrix_sessions(string_table)
    result = list(discover_citrix_sessions(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"active": (60, 65), "inactive": (10, 15), "total": (60, 65)},
            [["sessions", "1"], ["active_sessions", "1"], ["inactive_sessions", "0"]],
            [
                (0, "Total: 1.00", [("total", 1, 60, 65)]),
                (0, "Active: 1.00", [("active", 1, 60, 65)]),
                (0, "Inactive: 0.00", [("inactive", 0, 10, 15)]),
            ],
        ),
    ],
)
def test_check_citrix_sessions(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for citrix_sessions check."""
    parsed = parse_citrix_sessions(string_table)
    result = list(check_citrix_sessions(item, params, parsed))
    assert result == expected_results
