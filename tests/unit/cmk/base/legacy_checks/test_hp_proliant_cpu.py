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
from cmk.base.legacy_checks.hp_proliant_cpu import (
    check_hp_proliant_cpu,
    discover_hp_proliant_cpu,
    parse_hp_proliant_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["0", "0", "Intel Xeon", "2"], ["1", "0", "Intel Xeon", "2"]], [("0", {}), ("1", {})]),
    ],
)
def test_discover_hp_proliant_cpu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hp_proliant_cpu check."""
    parsed = parse_hp_proliant_cpu(string_table)
    result = list(discover_hp_proliant_cpu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "0",
            {},
            [["0", "0", "Intel Xeon", "2"], ["1", "0", "Intel Xeon", "2"]],
            [0, 'CPU0 "Intel Xeon" in slot 0 is in state "ok"'],
        ),
        (
            "1",
            {},
            [["0", "0", "Intel Xeon", "2"], ["1", "0", "Intel Xeon", "2"]],
            [0, 'CPU1 "Intel Xeon" in slot 0 is in state "ok"'],
        ),
    ],
)
def test_check_hp_proliant_cpu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hp_proliant_cpu check."""
    parsed = parse_hp_proliant_cpu(string_table)
    result = list(check_hp_proliant_cpu(item, params, parsed))
    assert result == expected_results
