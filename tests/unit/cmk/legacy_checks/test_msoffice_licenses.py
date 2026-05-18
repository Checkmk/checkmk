#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.msoffice_licenses import (
    check_msoffice_licenses,
    discover_msoffice_licenses,
    parse_msoffice_licenses,
)

STRING_TABLE = [
    ["sx:MYLICENSE1", "55", "0", "55"],
    ["sx:MYLICENSE2", "1000000", "0", ""],
    ["sx:MYLICENSE3"],
    ["sx:MYLICENSE4", "130", "0", "120"],
    ["sx:MYLICENSE5", "10000", "0", "1"],
    ["sx:MYLICENSE6", "6575", "0", "6330"],
    ["sx:MYLICENSE7", "3800", "0", "3756"],
    ["sx:MYLICENSE8", "10000", "0", "1424"],
    ["sx:MYLICENSE9", "10000", "0", "4"],
    ["sx:MYLICENSE10", "10000", "0", "5"],
    ["sx:MYLICENSE11", "100", "0", "46"],
    ["sx:MYLICENSE12", "1000000", "0", "194"],
    ["sx:MYLICENSE12", "5925", "0", "1"],
    ["sx:MYLICENSE12", "3600", "0", "5"],
    ["sx:MYLICENSE13", "10665", "0", "10461"],
    ["sx:MYLICENSE13", "840", "0", "803"],
    ["sx:MYLICENSE14", "0", "0", "2"],
    ["sx:MYLICENSE15", "0", "0", "0"],
    ["sx:MYLICENSE16", "5", "1", "4"],
]


def test_discover_msoffice_licenses() -> None:
    parsed = parse_msoffice_licenses(STRING_TABLE)
    result = sorted(discover_msoffice_licenses(parsed), key=lambda s: s.item or "")
    assert result == [
        Service(item="sx:MYLICENSE1"),
        Service(item="sx:MYLICENSE10"),
        Service(item="sx:MYLICENSE11"),
        Service(item="sx:MYLICENSE12"),
        Service(item="sx:MYLICENSE13"),
        Service(item="sx:MYLICENSE14"),
        Service(item="sx:MYLICENSE15"),
        Service(item="sx:MYLICENSE16"),
        Service(item="sx:MYLICENSE4"),
        Service(item="sx:MYLICENSE5"),
        Service(item="sx:MYLICENSE6"),
        Service(item="sx:MYLICENSE7"),
        Service(item="sx:MYLICENSE8"),
        Service(item="sx:MYLICENSE9"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        (
            "sx:MYLICENSE1",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 55"),
                Metric("licenses", 55),
                Result(state=State.OK, summary="Active licenses: 55"),
                Metric("licenses_total", 55),
                Result(
                    state=State.CRIT,
                    summary="Usage: 100.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("license_percentage", 100.0, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
        (
            "sx:MYLICENSE10",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 5"),
                Metric("licenses", 5),
                Result(state=State.OK, summary="Active licenses: 10000"),
                Metric("licenses_total", 10000),
                Result(state=State.OK, summary="Usage: 0.05%"),
                Metric("license_percentage", 0.05, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
        (
            "sx:MYLICENSE11",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 46"),
                Metric("licenses", 46),
                Result(state=State.OK, summary="Active licenses: 100"),
                Metric("licenses_total", 100),
                Result(state=State.OK, summary="Usage: 46.00%"),
                Metric("license_percentage", 46.0, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
        (
            "sx:MYLICENSE12",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 194"),
                Metric("licenses", 194),
                Result(state=State.OK, summary="Active licenses: 1000000"),
                Metric("licenses_total", 1000000),
                Result(state=State.OK, summary="Usage: 0.02%"),
                Metric("license_percentage", 0.0194, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
        (
            "sx:MYLICENSE13",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 10461"),
                Metric("licenses", 10461),
                Result(state=State.OK, summary="Active licenses: 10665"),
                Metric("licenses_total", 10665),
                Result(
                    state=State.CRIT,
                    summary="Usage: 98.09% (warn/crit at 80.00%/90.00%)",
                ),
                Metric(
                    "license_percentage",
                    98.08720112517581,
                    levels=(80.0, 90.0),
                    boundaries=(0, 100),
                ),
            ],
        ),
        (
            "sx:MYLICENSE14",
            {"usage": (80.0, 90.0)},
            [Result(state=State.OK, summary="No active licenses")],
        ),
        (
            "sx:MYLICENSE15",
            {"usage": (80.0, 90.0)},
            [Result(state=State.OK, summary="No active licenses")],
        ),
        (
            "sx:MYLICENSE16",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 4"),
                Metric("licenses", 4),
                Result(state=State.OK, summary="Active licenses: 5"),
                Metric("licenses_total", 5),
                Result(
                    state=State.WARN,
                    summary="Usage: 80.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("license_percentage", 80.0, levels=(80.0, 90.0), boundaries=(0, 100)),
                Result(state=State.OK, summary=" Warning units: 1"),
            ],
        ),
        (
            "sx:MYLICENSE4",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 120"),
                Metric("licenses", 120),
                Result(state=State.OK, summary="Active licenses: 130"),
                Metric("licenses_total", 130),
                Result(
                    state=State.CRIT,
                    summary="Usage: 92.31% (warn/crit at 80.00%/90.00%)",
                ),
                Metric(
                    "license_percentage",
                    92.3076923076923,
                    levels=(80.0, 90.0),
                    boundaries=(0, 100),
                ),
            ],
        ),
        (
            "sx:MYLICENSE5",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 1"),
                Metric("licenses", 1),
                Result(state=State.OK, summary="Active licenses: 10000"),
                Metric("licenses_total", 10000),
                Result(state=State.OK, summary="Usage: 0.01%"),
                Metric("license_percentage", 0.01, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
        (
            "sx:MYLICENSE6",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 6330"),
                Metric("licenses", 6330),
                Result(state=State.OK, summary="Active licenses: 6575"),
                Metric("licenses_total", 6575),
                Result(
                    state=State.CRIT,
                    summary="Usage: 96.27% (warn/crit at 80.00%/90.00%)",
                ),
                Metric(
                    "license_percentage",
                    96.27376425855513,
                    levels=(80.0, 90.0),
                    boundaries=(0, 100),
                ),
            ],
        ),
        (
            "sx:MYLICENSE7",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 3756"),
                Metric("licenses", 3756),
                Result(state=State.OK, summary="Active licenses: 3800"),
                Metric("licenses_total", 3800),
                Result(
                    state=State.CRIT,
                    summary="Usage: 98.84% (warn/crit at 80.00%/90.00%)",
                ),
                Metric(
                    "license_percentage",
                    98.84210526315789,
                    levels=(80.0, 90.0),
                    boundaries=(0, 100),
                ),
            ],
        ),
        (
            "sx:MYLICENSE8",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 1424"),
                Metric("licenses", 1424),
                Result(state=State.OK, summary="Active licenses: 10000"),
                Metric("licenses_total", 10000),
                Result(state=State.OK, summary="Usage: 14.24%"),
                Metric("license_percentage", 14.24, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
        (
            "sx:MYLICENSE9",
            {"usage": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Consumed licenses: 4"),
                Metric("licenses", 4),
                Result(state=State.OK, summary="Active licenses: 10000"),
                Metric("licenses_total", 10000),
                Result(state=State.OK, summary="Usage: 0.04%"),
                Metric("license_percentage", 0.04, levels=(80.0, 90.0), boundaries=(0, 100)),
            ],
        ),
    ],
)
def test_check_msoffice_licenses(
    item: str, params: Mapping[str, Any], expected_results: Sequence[Result | Metric]
) -> None:
    parsed = parse_msoffice_licenses(STRING_TABLE)
    result = list(check_msoffice_licenses(item, params, parsed))
    assert result == expected_results
