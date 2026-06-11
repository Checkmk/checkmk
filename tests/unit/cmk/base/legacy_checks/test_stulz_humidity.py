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
    inventory_stulz_humidity,
    parse_stulz_humidity,
)

# OIDEnd is "{bus}.{unit}.{subindex}"; the device exposes units on two buses.
# Readings are in per-mille and divided by 10 by the check.
_STRING_TABLE: StringTable = [
    ["1.1.1", "339"],
    ["1.2.1", "332"],
    ["2.1.1", "500"],
    ["2.2.1", "308"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            [
                ("1-1", {}),
                ("1-2", {}),
                ("2-1", {}),
                ("2-2", {}),
            ],
        ),
    ],
)
def test_inventory_stulz_humidity(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for stulz_humidity check."""
    parsed = parse_stulz_humidity(string_table)
    result = list(inventory_stulz_humidity(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1-1",
            {"levels_lower": (40.0, 35.0), "levels": (60.0, 65.0)},
            _STRING_TABLE,
            [2, "33.90% (warn/crit below 40.00%/35.00%)", [("humidity", 33.9, 60.0, 65.0, 0, 100)]],
        ),
        (
            "2-1",
            {"levels_lower": (40.0, 35.0), "levels": (60.0, 65.0)},
            _STRING_TABLE,
            [0, "50.00%", [("humidity", 50.0, 60.0, 65.0, 0, 100)]],
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
