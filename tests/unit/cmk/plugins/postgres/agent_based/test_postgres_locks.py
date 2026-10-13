#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.postgres.agent_based.postgres_locks import (
    check_postgres_locks,
    discover_postgres_locks,
)
from cmk.plugins.postgres.lib import parse_dbs

SECTION = parse_dbs(
    [
        ["[databases_start]"],
        ["postgres"],
        ["zweitedb"],
        ["[databases_end]"],
        ["datname", "granted", "mode"],
        ["postgres", "t", "AccessShareLock"],
        ["postgres", "t", "AccessShareLock"],
        ["postgres", "t", "AccessShareLock"],
        ["postgres", "t", "ExclusiveLock"],
        ["postgres", "", "ExclusiveLock"],
        ["zweitedb", "", ""],
        ["template1", "", ""],
    ]
)


def test_every_database_is_discovered() -> None:
    assert list(discover_postgres_locks(SECTION)) == [
        Service(item="postgres"),
        Service(item="zweitedb"),
    ]


def test_only_granted_locks_are_counted() -> None:
    assert list(check_postgres_locks("postgres", {}, SECTION)) == [
        Result(state=State.OK, summary="Access Share Locks 3"),
        Metric("shared_locks", 3),
        Result(state=State.OK, summary="Exclusive Locks 1"),
        Metric("exclusive_locks", 1),
    ]


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {"levels_shared": (2, 4)},
            Result(state=State.WARN, summary="too high (Levels at 2/4)"),
            id="shared warn",
        ),
        pytest.param(
            {"levels_shared": (1, 3)},
            Result(state=State.CRIT, summary="too high (Levels at 1/3)"),
            id="shared crit",
        ),
        pytest.param(
            {"levels_exclusive": (1, 2)},
            Result(state=State.WARN, summary="too high (Levels at 1/2)"),
            id="exclusive warn",
        ),
        pytest.param(
            {"levels_exclusive": (0, 1)},
            Result(state=State.CRIT, summary="too high (Levels at 0/1)"),
            id="exclusive crit",
        ),
    ],
)
def test_lock_counts_are_checked_against_levels(
    params: dict[str, tuple[int, int]], expected: Result
) -> None:
    assert expected in list(check_postgres_locks("postgres", params, SECTION))


def test_database_without_locks_reports_zero() -> None:
    assert list(check_postgres_locks("zweitedb", {}, SECTION)) == [
        Result(state=State.OK, summary="Access Share Locks 0"),
        Metric("shared_locks", 0),
        Result(state=State.OK, summary="Exclusive Locks 0"),
        Metric("exclusive_locks", 0),
    ]


def test_unknown_database_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_postgres_locks("template1", {}, SECTION))
