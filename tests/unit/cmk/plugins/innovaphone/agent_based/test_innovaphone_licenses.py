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
    parse_innovaphone_licenses,
)

_SECTION: StringTable = [["100", "50"]]


def test_parse_innovaphone_licenses_keeps_string_table() -> None:
    assert parse_innovaphone_licenses(_SECTION) == _SECTION


def test_discover_innovaphone_licenses() -> None:
    assert list(discover_innovaphone_licenses(_SECTION)) == [Service()]


def test_discover_innovaphone_licenses_no_data() -> None:
    assert list(discover_innovaphone_licenses([])) == []


def test_check_innovaphone_licenses_no_data_returns_nothing() -> None:
    assert list(check_innovaphone_licenses({"levels": (90.0, 95.0)}, [])) == []


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"levels": (90.0, 95.0)},
            [["0", "0"]],
            [
                Result(state=State.UNKNOWN, summary="Used 0/0 Licences"),
                Metric("licenses", 0.0, boundaries=(0.0, 0.0)),
            ],
            id="zero values",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            [["100", "0"]],
            [
                Result(state=State.OK, summary="Used 0/100 Licences (0%)"),
                Metric("licenses", 0.0, boundaries=(0.0, 100.0)),
            ],
            id="zero utilization with nonzero total",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            [["100", "50"]],
            [
                Result(state=State.OK, summary="Used 50/100 Licences (50%)"),
                Metric("licenses", 50.0, boundaries=(0.0, 100.0)),
            ],
            id="ok state",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            [["100", "90"]],
            [
                Result(state=State.OK, summary="Used 90/100 Licences (90%)"),
                Metric("licenses", 90.0, boundaries=(0.0, 100.0)),
            ],
            id="ok state at warn boundary",
        ),
        pytest.param(
            {"levels": (90.0, 95.0)},
            [["100", "92"]],
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
            [["100", "95"]],
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
            [["100", "96"]],
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
            [["100", "110"]],
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
    params: Mapping[str, Any], section: StringTable, expected: list[Result | Metric]
) -> None:
    assert list(check_innovaphone_licenses(params, section)) == expected
