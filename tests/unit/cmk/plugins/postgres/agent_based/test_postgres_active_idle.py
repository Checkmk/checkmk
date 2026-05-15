#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.postgres.agent_based.postgres_connections import (
    check_postgres_connections,
    discover_postgres_connections,
)
from cmk.plugins.postgres.lib import parse_dbs


def parsed() -> Mapping[str, Sequence[Mapping[str, str]]]:
    """Parse postgres connections test data using actual parse function."""
    string_table = [
        ["[databases_start]"],
        ["postgres"],
        ["app"],
        ["app_test"],
        ["[databases_end]"],
        ["datname", "mc", "idle", "active"],
        ["postgres", "100", "4", "9"],
        ["", "100", "0", "0"],
        ["app", "100", "1", "0"],
        ["app_test", "100", "2", "0"],
    ]

    return parse_dbs(string_table)


def test_postgres_connections_discovery() -> None:
    discovery_result = list(discover_postgres_connections(parsed()))
    expected = [Service(item="app"), Service(item="app_test"), Service(item="postgres")]
    assert sorted(discovery_result, key=lambda s: s.item or "") == sorted(
        expected, key=lambda s: s.item or ""
    )


def test_postgres_connections_check_app() -> None:
    params = {
        "levels_perc_active": (80.0, 90.0),
        "levels_perc_idle": (80.0, 90.0),
    }

    results = list(check_postgres_connections("app", params, parsed()))

    # active=0 (string "0" is truthy, so not skipped); idle=1
    assert results == [
        Result(state=State.OK, summary="Used active connections: 0"),
        Metric("active_connections", 0.0, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Used active percentage: 0%"),
        Result(state=State.OK, summary="Used idle connections: 1"),
        Metric("idle_connections", 1.0, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Used idle percentage: 1.00%"),
    ]


def test_postgres_connections_check_app_test_warning() -> None:
    params = {"levels_perc_active": (80.0, 90.0), "levels_perc_idle": (1.0, 5.0)}

    results = list(check_postgres_connections("app_test", params, parsed()))

    # active=0 -> skipped; idle=2, percentage 2% triggers WARN
    assert isinstance(results[-1], Result)
    assert results[-1].state == State.WARN
    assert "Used idle percentage: 2.00%" in results[-1].summary
    assert "warn/crit at 1.00%/5.00%" in results[-1].summary


def test_postgres_connections_check_postgres_critical() -> None:
    params = {
        "levels_perc_active": (80.0, 90.0),
        "levels_perc_idle": (80.0, 90.0),
        "levels_abs_active": (2, 5),
    }

    results = list(check_postgres_connections("postgres", params, parsed()))

    assert isinstance(results[0], Result)
    assert results[0].state == State.CRIT
    assert "Used active connections: 9" in results[0].summary
    assert "warn/crit at 2/5" in results[0].summary


def test_postgres_connections_check_missing_item() -> None:
    params = {"levels_perc_active": (80.0, 90.0), "levels_perc_idle": (80.0, 90.0)}

    with pytest.raises(IgnoreResultsError):
        list(check_postgres_connections("nonexistent", params, parsed()))
