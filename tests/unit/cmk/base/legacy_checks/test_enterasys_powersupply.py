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
from cmk.base.legacy_checks.enterasys_powersupply import (
    check_enterasys_powersupply,
    discover_enterasys_powersupply,
    parse_enterasys_powersupply,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["101", "3", "1", "1"], ["102", "", "", "1"]], [("101", {})]),
    ],
)
def test_discover_enterasys_powersupply(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for enterasys_powersupply check."""
    parsed = parse_enterasys_powersupply(string_table)
    result = list(discover_enterasys_powersupply(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "101",
            {"redundancy_ok_states": [1]},
            [["101", "3", "1", "1"], ["102", "", "", "1"]],
            [0, "Status: working and redundant (ac-dc)"],
        ),
    ],
)
def test_check_enterasys_powersupply(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for enterasys_powersupply check."""
    parsed = parse_enterasys_powersupply(string_table)
    result = list(check_enterasys_powersupply(item, params, parsed))
    assert result == expected_results
