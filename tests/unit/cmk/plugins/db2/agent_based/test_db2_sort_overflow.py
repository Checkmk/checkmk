#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.db2.agent_based.db2_sort_overflow import (
    check_db2_sort_overflow,
    discover_db2_sort_overflow,
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

SECTION = parse_db2_dbs(
    [
        ["TIMESTAMP", "1426595137"],
        ["[[[test:datenbank1]]]"],
        ["Total", "sorts", "100"],
        ["Sort", "overflows", "3"],
        ["[[[test:nosorts]]]"],
        ["Total", "sorts", "0"],
        ["Sort", "overflows", "0"],
        ["[[[test:loginfailed]]]"],
    ]
)


def test_global_timestamp_is_parsed() -> None:
    assert SECTION[0] == 1426595137


def test_every_database_is_discovered() -> None:
    assert list(discover_db2_sort_overflow(SECTION)) == [
        Service(item="test:datenbank1"),
        Service(item="test:nosorts"),
        Service(item="test:loginfailed"),
    ]


@pytest.mark.parametrize(
    "levels, expected",
    [
        pytest.param((5.0, 10.0), Result(state=State.OK, summary="3.0% sort overflow"), id="ok"),
        pytest.param(
            (2.0, 4.0),
            Result(state=State.WARN, summary="3.0% sort overflow (levels at 2.0%/4.0%)"),
            id="warn",
        ),
        pytest.param(
            (1.0, 3.0),
            Result(state=State.CRIT, summary="3.0% sort overflow (levels at 1.0%/3.0%)"),
            id="crit",
        ),
    ],
)
def test_overflow_percentage_is_checked_against_levels(
    levels: tuple[float, float], expected: Result
) -> None:
    assert (
        next(iter(check_db2_sort_overflow("test:datenbank1", {"levels_perc": levels}, SECTION)))
        == expected
    )


def test_counters_and_metric_are_reported() -> None:
    assert list(check_db2_sort_overflow("test:datenbank1", {"levels_perc": (2.0, 4.0)}, SECTION))[
        1:
    ] == [
        Result(state=State.OK, summary="Sort overflows: 3"),
        Result(state=State.OK, summary="Total sorts: 100"),
        Metric("sort_overflow", 3.0, levels=(2.0, 4.0), boundaries=(0, 100)),
    ]


def test_no_sorts_means_no_overflow() -> None:
    assert next(
        iter(check_db2_sort_overflow("test:nosorts", {"levels_perc": (2.0, 4.0)}, SECTION))
    ) == Result(state=State.OK, summary="0.0% sort overflow")


def test_database_without_data_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_db2_sort_overflow("test:loginfailed", {"levels_perc": (2.0, 4.0)}, SECTION))
