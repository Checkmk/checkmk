#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.juniper_bgp_state import (
    check_juniper_bgp_state,
    discover_juniper_bgp_state,
    parse_juniper_bgp_state,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]],
            [("100.96.1.34", {}), ("100.96.1.38", {})],
        ),
    ],
)
def test_discover_juniper_bgp_state(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for juniper_bgp_state check."""
    parsed = parse_juniper_bgp_state(string_table)
    result = list(discover_juniper_bgp_state(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "100.96.1.34",
            {},
            [["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]],
            [
                (0, "Status with peer 100.96.1.34 is established"),
                (0, "operational status: running"),
            ],
        ),
        (
            "100.96.1.38",
            {},
            [["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]],
            [(2, "Status with peer 100.96.1.38 is active"), (0, "operational status: running")],
        ),
    ],
)
def test_check_juniper_bgp_state(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for juniper_bgp_state check."""
    parsed = parse_juniper_bgp_state(string_table)
    result = list(check_juniper_bgp_state(item, params, parsed))
    assert result == expected_results
