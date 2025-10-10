#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.mbg_lantime_ng_fan import (
    check_mbg_lantime_ng_fan,
    discover_mbg_lantime_ng_fan,
    parse_mbg_lantime_ng_fan,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [("1", {}), ("2", {}), ("4", {}), ("5", {})],
        ),
    ],
)
def test_discover_mbg_lantime_ng_fan(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mbg_lantime_ng_fan check."""
    parsed = parse_mbg_lantime_ng_fan(string_table)
    result = list(discover_mbg_lantime_ng_fan(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {},
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [(0, "Status: on"), (0, "Errors: no")],
        ),
        (
            "2",
            {},
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [(0, "Status: on"), (0, "Errors: no")],
        ),
        (
            "4",
            {},
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [(0, "Status: on"), (0, "Errors: no")],
        ),
        (
            "5",
            {},
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [(0, "Status: on"), (3, "Errors: not available")],
        ),
    ],
)
def test_check_mbg_lantime_ng_fan(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for mbg_lantime_ng_fan check."""
    parsed = parse_mbg_lantime_ng_fan(string_table)
    result = list(check_mbg_lantime_ng_fan(item, params, parsed))
    assert result == expected_results
