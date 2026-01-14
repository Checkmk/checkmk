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
from cmk.base.legacy_checks.watchdog_sensors import (
    check_watchdog_sensors,
    discover_watchdog_sensors,
    parse_watchdog_sensors,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [["3.2.0", "1"]],
                [
                    ["1", "First Floor Ambient", "1", "213", "37", "60", ""],
                    ["2", "Second Floor Ambient", "1", "200", "30", "40", ""],
                ],
            ],
            [("Watchdog 1", {}), ("Watchdog 2", {})],
        ),
    ],
)
def test_discover_watchdog_sensors(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for watchdog_sensors check."""
    parsed = parse_watchdog_sensors(string_table)
    result = list(discover_watchdog_sensors(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Watchdog 1",
            {},
            [
                [["3.2.0", "1"]],
                [
                    ["1", "First Floor Ambient", "1", "213", "37", "60", ""],
                    ["2", "Second Floor Ambient", "1", "200", "30", "40", ""],
                ],
            ],
            [(0, "available"), (0, "Location: First Floor Ambient")],
        ),
        (
            "Watchdog 2",
            {},
            [
                [["3.2.0", "1"]],
                [
                    ["1", "First Floor Ambient", "1", "213", "37", "60", ""],
                    ["2", "Second Floor Ambient", "1", "200", "30", "40", ""],
                ],
            ],
            [(0, "available"), (0, "Location: Second Floor Ambient")],
        ),
    ],
)
def test_check_watchdog_sensors(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for watchdog_sensors check."""
    parsed = parse_watchdog_sensors(string_table)
    result = list(check_watchdog_sensors(item, params, parsed))
    assert result == expected_results
