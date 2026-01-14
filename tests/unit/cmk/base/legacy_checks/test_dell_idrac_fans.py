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
from cmk.base.legacy_checks.dell_idrac_fans import (
    check_dell_idrac_fans,
    discover_dell_idrac_fans,
    parse_dell_idrac_fans,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["1", "1", "", "System Board Fan1A", "", "", "", ""],
                ["2", "2", "", "System Board Fan1B", "", "", "", ""],
                ["3", "10", "", "System Board Fan2A", "", "", "", ""],
            ],
            [("3", {})],
        ),
    ],
)
def test_discover_dell_idrac_fans(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for dell_idrac_fans check."""
    parsed = parse_dell_idrac_fans(string_table)
    result = list(discover_dell_idrac_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "3",
            {},
            [
                ["1", "1", "", "System Board Fan1A", "", "", "", ""],
                ["2", "2", "", "System Board Fan1B", "", "", "", ""],
                ["3", "10", "", "System Board Fan2A", "", "", "", ""],
            ],
            [(2, "Status: FAILED, Name: System Board Fan2A")],
        ),
    ],
)
def test_check_dell_idrac_fans(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for dell_idrac_fans check."""
    parsed = parse_dell_idrac_fans(string_table)
    result = list(check_dell_idrac_fans(item, params, parsed))
    assert result == expected_results
