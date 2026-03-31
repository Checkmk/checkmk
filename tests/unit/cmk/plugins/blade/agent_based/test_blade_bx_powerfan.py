#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.blade.agent_based.blade_bx_powerfan import (
    check_blade_bx_powerfan,
    discover_blade_bx_powerfan,
    parse_blade_bx_powerfan,
)

STRING_TABLE_1 = [
    ["3", "Fan-1", "500", "1000", "6400", "2"],
    ["3", "Fan-2", "250", "1000", "5248", "2"],
    ["3", "Fan-3", "900", "1000", "5248", "2"],
    ["8", "Fan-4", "500", "1000", "5248", "2"],  # status=not-present
    ["4", "Fan-5", "500", "1000", "5248", "2"],  # status=fail
    ["1", "Fan-6", "500", "1000", "5248", "0"],  # ctrlstate
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                Service(item="Fan-1"),
                Service(item="Fan-2"),
                Service(item="Fan-3"),
                Service(item="Fan-5"),
                Service(item="Fan-6"),
            ],
        ),
    ],
)
def test_discover_blade_bx_powerfan(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_blade_bx_powerfan(string_table)
    result = list(discover_blade_bx_powerfan(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            {
                "Fan-1": [
                    Result(state=State.OK, summary="Speed at 500 RPM: 50.0%"),
                    Metric("perc", 50.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                    Metric("rpm", 500.0),
                ],
                "Fan-2": [
                    Result(
                        state=State.WARN,
                        summary="Speed at 250 RPM: 25.0% (warn/crit below 30.0%/20.0%)",
                    ),
                    Metric("perc", 25.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                    Metric("rpm", 250.0),
                ],
                "Fan-3": [
                    Result(
                        state=State.CRIT,
                        summary="Speed at 900 RPM: 90.0% (warn/crit at 80.0%/90.0%)",
                    ),
                    Metric("perc", 90.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                    Metric("rpm", 900.0),
                ],
                "Fan-5": [
                    Result(state=State.CRIT, summary="Status: fail"),
                    Metric("perc", 50.0, boundaries=(0.0, 100.0)),
                    Metric("rpm", 500.0),
                ],
                "Fan-6": [
                    Result(state=State.CRIT, summary="Fan not present or poweroff"),
                    Metric("perc", 50.0, boundaries=(0.0, 100.0)),
                    Metric("rpm", 500.0),
                ],
            },
        ),
    ],
)
def test_check_blade_bx_powerfan(
    string_table: StringTable, expected_results: Mapping[str, CheckResult]
) -> None:
    parsed = parse_blade_bx_powerfan(string_table)
    services = list(discover_blade_bx_powerfan(parsed))
    params = {"levels": (80, 90), "levels_lower": (30, 20)}
    result = {
        service.item: list(check_blade_bx_powerfan(service.item, params, parsed))
        for service in services
        if service.item is not None
    }
    assert result == expected_results
