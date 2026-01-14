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
from cmk.base.legacy_checks.stulz_humidity import (
    check_stulz_humidity,
    discover_stulz_humidity,
    parse_stulz_humidity,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["MICOS11Q", "12", "229376", "15221", "15221", "NO"],
                ["MICOS11Q", "12", "229376", "15221", "15221"],
            ],
            [("MICOS11Q", {}), ("MICOS11Q", {})],
        ),
    ],
)
def test_discover_stulz_humidity(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for stulz_humidity check."""
    parsed = parse_stulz_humidity(string_table)
    result = list(discover_stulz_humidity(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "MICOS11Q",
            {"levels_lower": (40.0, 35.0), "levels": (60.0, 65.0)},
            [
                ["MICOS11Q", "12", "229376", "15221", "15221", "NO"],
                ["MICOS11Q", "12", "229376", "15221", "15221"],
            ],
            [2, "1.20% (warn/crit below 40.00%/35.00%)", [("humidity", 1.2, 60.0, 65.0, 0, 100)]],
        ),
        (
            "MICOS11Q",
            {"levels_lower": (40.0, 35.0), "levels": (60.0, 65.0)},
            [
                ["MICOS11Q", "12", "229376", "15221", "15221", "NO"],
                ["MICOS11Q", "12", "229376", "15221", "15221"],
            ],
            [2, "1.20% (warn/crit below 40.00%/35.00%)", [("humidity", 1.2, 60.0, 65.0, 0, 100)]],
        ),
    ],
)
def test_check_stulz_humidity(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for stulz_humidity check."""
    parsed = parse_stulz_humidity(string_table)
    result = list(check_stulz_humidity(item, params, parsed))
    assert result == expected_results
