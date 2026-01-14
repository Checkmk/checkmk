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
from cmk.base.legacy_checks.fsc_fans import check_fsc_fans, discover_fsc_fans, parse_fsc_fans


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["NULL", "NULL"], ["FAN1 SYS", "4140"]], [("FAN1 SYS", {})]),
    ],
)
def test_discover_fsc_fans(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for fsc_fans check."""
    parsed = parse_fsc_fans(string_table)
    result = list(discover_fsc_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "FAN1 SYS",
            {"lower": (2000, 1000)},
            [["NULL", "NULL"], ["FAN1 SYS", "4140"]],
            [(0, "Speed: 4140 RPM", [])],
        ),
    ],
)
def test_check_fsc_fans(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for fsc_fans check."""
    parsed = parse_fsc_fans(string_table)
    result = list(check_fsc_fans(item, params, parsed))
    assert result == expected_results
