#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.postgres.agent_based.postgres_sessions import (
    check_postgres_sessions,
    discover_postgres_sessions,
    parse_postgres_sessions,
)

SECTION = parse_postgres_sessions(
    [
        ["f", "1"],
        ["t", "4"],
        ["[[[foobar]]]"],
        ["t", "2"],
    ]
)


def test_missing_lines_default_to_zero() -> None:
    assert SECTION == {
        "": {"total": 4, "running": 1},
        "FOOBAR": {"total": 2, "running": 0},
    }


def test_every_instance_is_discovered() -> None:
    section = parse_postgres_sessions([["[[[foo]]]"], ["t", "1"], ["[[[bar]]]"], ["f", "2"]])

    assert list(discover_postgres_sessions(section)) == [
        Service(item="FOO"),
        Service(item="BAR"),
    ]


def test_total_adds_idle_and_running_sessions() -> None:
    assert list(check_postgres_sessions("", {}, SECTION)) == [
        Result(state=State.OK, summary="Total: 5"),
        Metric("total", 5),
        Result(state=State.OK, summary="Running: 1"),
        Metric("running", 1),
    ]


def test_session_counts_are_checked_against_levels() -> None:
    assert list(check_postgres_sessions("", {"total": (3, 5), "running": (1, 2)}, SECTION)) == [
        Result(state=State.CRIT, summary="Total: 5 (warn/crit at 3/5)"),
        Metric("total", 5, levels=(3, 5)),
        Result(state=State.WARN, summary="Running: 1 (warn/crit at 1/2)"),
        Metric("running", 1, levels=(1, 2)),
    ]


def test_missing_instance_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_postgres_sessions("OTHER", {}, SECTION))
