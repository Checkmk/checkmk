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
from cmk.base.legacy_checks.pulse_secure_disk_util import (
    check_pulse_secure_disk_util,
    discover_pulse_secure_disk_util,
    parse_pulse_secure_disk_util,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["7"]], [(None, {})]),
    ],
)
def test_discover_pulse_secure_disk(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for pulse_secure_disk_util check."""
    parsed = parse_pulse_secure_disk_util(string_table)
    if parsed is not None:
        result = list(discover_pulse_secure_disk_util(parsed))
    else:
        result = []
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"upper_levels": (80.0, 90.0)},
            [["7"]],
            [(0, "Percentage of disk space used: 7.00%", [("disk_utilization", 7, 80.0, 90.0)])],
        ),
    ],
)
def test_check_pulse_secure_disk(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for pulse_secure_disk_util check."""
    parsed = parse_pulse_secure_disk_util(string_table)
    result = list(check_pulse_secure_disk_util(item, params, parsed))
    assert result == expected_results
