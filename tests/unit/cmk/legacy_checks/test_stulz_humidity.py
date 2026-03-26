#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.stulz_humidity import (
    check_stulz_humidity,
    discover_stulz_humidity,
    parse_stulz_humidity,
)

_STRING_TABLE: list[list[str]] = [
    ["MICOS11Q", "12", "229376", "15221", "15221", "NO"],
    ["MICOS11Q", "12", "229376", "15221", "15221"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            [Service(item="MICOS11Q"), Service(item="MICOS11Q")],
        ),
    ],
)
def test_discover_stulz_humidity(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_stulz_humidity(string_table)
    result = list(discover_stulz_humidity(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "MICOS11Q",
            {"levels_lower": (40.0, 35.0), "levels": (60.0, 65.0)},
            _STRING_TABLE,
            [
                Result(
                    state=State.CRIT,
                    summary="1.20% (warn/crit below 40.00%/35.00%)",
                ),
                Metric("humidity", 1.2, levels=(60.0, 65.0), boundaries=(0.0, 100.0)),
            ],
        ),
    ],
)
def test_check_stulz_humidity(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    parsed = parse_stulz_humidity(string_table)
    result = list(check_stulz_humidity(item, params, parsed))
    assert result == expected_results
