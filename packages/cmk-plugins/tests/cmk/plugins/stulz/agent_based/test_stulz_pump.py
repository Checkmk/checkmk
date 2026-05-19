#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc,import-untyped"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.stulz.agent_based.stulz_pump import (
    check_stulz_pump,
    discover_stulz_pump,
    parse_stulz_pump,
)

_SECTION: Sequence[StringTable] = [
    [
        ["1.1", "1"],
        ["2.1", "0"],
        ["3.1", "7"],
    ],
    [
        ["75"],
        ["0"],
        ["42"],
    ],
]


def test_discover_stulz_pump() -> None:
    parsed = parse_stulz_pump(_SECTION)
    assert list(discover_stulz_pump(parsed)) == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "1",
            [
                Result(state=State.OK, summary="Pump is running at 75%"),
                Metric("rpm", 75.0, boundaries=(0.0, 100.0)),
            ],
        ),
        (
            "2",
            [
                Result(state=State.CRIT, summary="Pump is not running"),
                Metric("rpm", 0.0, boundaries=(0.0, 100.0)),
            ],
        ),
        (
            "3",
            [
                Result(state=State.UNKNOWN, summary="Pump reports unidentified status 7"),
                Metric("rpm", 42.0, boundaries=(0.0, 100.0)),
            ],
        ),
        ("does-not-exist", []),
    ],
)
def test_check_stulz_pump(item: str, expected_results: Sequence[Result | Metric]) -> None:
    parsed = parse_stulz_pump(_SECTION)
    assert list(check_stulz_pump(item, parsed)) == expected_results
