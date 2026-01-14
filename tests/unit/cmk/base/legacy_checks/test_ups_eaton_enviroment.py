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
from cmk.base.legacy_checks.ups_eaton_enviroment import (
    check_ups_eaton_enviroment,
    discover_ups_eaton_enviroment,
    parse_ups_eaton_enviroment,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "40", "3"]], [(None, {})]),
    ],
)
def test_discover_ups_eaton_enviroment(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ups_eaton_enviroment check."""
    parsed = parse_ups_eaton_enviroment(string_table)
    result = list(discover_ups_eaton_enviroment(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"humidity": (65, 80), "remote_temp": (40, 50), "temp": (40, 50)},
            [["1", "40", "3"]],
            [
                (0, "Temperature: 1.0 °C", [("temp", 1, 40, 50)]),
                (
                    1,
                    "Remote-Temperature: 40.0 °C (warn/crit at 40.0 °C/50.0 °C)",
                    [("remote_temp", 40, 40, 50)],
                ),
                (0, "Humidity: 3.0%", [("humidity", 3, 65, 80)]),
            ],
        ),
    ],
)
def test_check_ups_eaton_enviroment(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ups_eaton_enviroment check."""
    parsed = parse_ups_eaton_enviroment(string_table)
    result = list(check_ups_eaton_enviroment(item, params, parsed))
    assert result == expected_results
