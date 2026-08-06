#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.innovaphone.agent_based.innovaphone_licenses import (
    check_innovaphone_licenses,
    discover_innovaphone_licenses,
    LicenseUsage,
    parse_innovaphone_licenses,
)


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([], id="empty payload"),
        pytest.param([[]], id="empty nested payload"),
        pytest.param([["not-a-number", "5"]], id="total a number"),
        pytest.param([["10", "not-a-number"]], id="used not a number"),
        pytest.param([["-1", "5"]], id="total negative"),
        pytest.param([["10", "-1"]], id="used negative"),
    ],
)
def test_parse_innovaphone_licenses_invalid_input(string_table: StringTable) -> None:
    assert parse_innovaphone_licenses(string_table) is None


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param([["10", "5"]], LicenseUsage(used=5, total=10), id="happy path"),
        pytest.param([["0", "0"]], LicenseUsage(used=0, total=0), id="zero values"),
        pytest.param([["5", "10"]], LicenseUsage(used=10, total=5), id="used > total"),
    ],
)
def test_parse_innovaphone_licenses(string_table: StringTable, expected: LicenseUsage) -> None:
    assert parse_innovaphone_licenses(string_table) == expected


def test_discover_innovaphone_licenses() -> None:
    section = LicenseUsage(used=5, total=10)
    assert list(discover_innovaphone_licenses(section)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=0, total=0),
            [
                Result(state=State.UNKNOWN, summary="Used 0/0 Licences"),
                Metric("licenses", 0.0, boundaries=(0.0, 0.0)),
            ],
            id="zero values",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=0, total=100),
            [
                Result(state=State.OK, summary="Used 0/100 Licences (0%)"),
                Metric("licenses", 0.0, boundaries=(0.0, 100.0)),
            ],
            id="zero utilization with nonzero total",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=50, total=100),
            [
                Result(state=State.OK, summary="Used 50/100 Licences (50%)"),
                Metric("licenses", 50.0, boundaries=(0.0, 100.0)),
            ],
            id="ok state",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=90, total=100),
            [
                Result(state=State.OK, summary="Used 90/100 Licences (90%)"),
                Metric("licenses", 90.0, boundaries=(0.0, 100.0)),
            ],
            id="ok state at warn boundary",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=92, total=100),
            [
                Result(
                    state=State.WARN,
                    summary="Used 92/100 Licences (92%)Warning/ Critical at (90.0/95.0)",
                ),
                Metric("licenses", 92.0, boundaries=(0.0, 100.0)),
            ],
            id="warn state",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=95, total=100),
            [
                Result(
                    state=State.WARN,
                    summary="Used 95/100 Licences (95%)Warning/ Critical at (90.0/95.0)",
                ),
                Metric("licenses", 95.0, boundaries=(0.0, 100.0)),
            ],
            id="warn state at crit boundary",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=96, total=100),
            [
                Result(
                    state=State.CRIT,
                    summary="Used 96/100 Licences (96%)Warning/ Critical at (90.0/95.0)",
                ),
                Metric("licenses", 96.0, boundaries=(0.0, 100.0)),
            ],
            id="crit state",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            LicenseUsage(used=110, total=100),
            [
                Result(
                    state=State.CRIT,
                    summary="Used 110/100 Licences (110%)Warning/ Critical at (90.0/95.0)",
                ),
                Metric("licenses", 110.0, boundaries=(0.0, 100.0)),
            ],
            id="used > total",
        ),
    ],
)
def test_check_innovaphone_licenses(
    params: Mapping[str, Any], section: LicenseUsage, expected: list[Result | Metric]
) -> None:
    assert list(check_innovaphone_licenses(params, section)) == expected
