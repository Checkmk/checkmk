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
from cmk.base.legacy_checks.steelhead_connections import (
    check_steelhead_connections,
    discover_steelhead_connections,
    parse_steelhead_connections,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["1.0", "1619"],
                ["2.0", "1390"],
                ["3.0", "0"],
                ["4.0", "4"],
                ["5.0", "1615"],
                ["6.0", "347"],
                ["7.0", "3009"],
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_steelhead_connections(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for steelhead_connections check."""
    parsed = parse_steelhead_connections(string_table)
    result = list(discover_steelhead_connections(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                ["1.0", "1619"],
                ["2.0", "1390"],
                ["3.0", "0"],
                ["4.0", "4"],
                ["5.0", "1615"],
                ["6.0", "347"],
                ["7.0", "3009"],
            ],
            [
                (0, "Total connections: 3009", []),
                (0, "Passthrough: 1390", [("passthrough", 1390)]),
                (0, "Optimized: 1619", []),
                (0, "Active: 347", [("active", 347)]),
                (0, "Established: 1615", [("established", 1615)]),
                (0, "Half opened: 0", [("halfOpened", 0)]),
                (0, "Half closed: 4", [("halfClosed", 4)]),
            ],
        ),
    ],
)
def test_check_steelhead_connections(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for steelhead_connections check."""
    parsed = parse_steelhead_connections(string_table)
    result = list(check_steelhead_connections(item, params, parsed))
    assert result == expected_results
