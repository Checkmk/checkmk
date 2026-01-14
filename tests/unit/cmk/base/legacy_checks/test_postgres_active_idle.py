#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import IgnoreResultsError
from cmk.base.legacy_checks.postgres_connections import (
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
    """Test discovery of postgres_connections items."""
    discovery_result = list(discover_postgres_connections(parsed()))

    expected: list[tuple[str, dict]] = [("app", {}), ("app_test", {}), ("postgres", {})]

    # Sort for comparison since order may vary
    assert sorted(discovery_result) == sorted(expected)


def test_postgres_connections_check_app() -> None:
    """Test check function for app database (normal case)."""
    params = {
        "levels_perc_active": (80.0, 90.0),
        "levels_perc_idle": (80.0, 90.0),
    }

    results = list(check_postgres_connections("app", params, parsed()))

    assert len(results) == 4

    # Check active connections
    state, summary, metrics = results[0]
    assert state == 0  # OK
    assert "Used active connections: 0" in summary
    assert metrics == [("active_connections", 0.0, None, None, 0, 100.0)]

    # Check active percentage
    state, summary, metrics = results[1]
    assert state == 0  # OK
    assert "Used active percentage: 0%" in summary
    assert metrics == []

    # Check idle connections
    state, summary, metrics = results[2]
    assert state == 0  # OK
    assert "Used idle connections: 1" in summary
    assert metrics == [("idle_connections", 1.0, None, None, 0, 100.0)]

    # Check idle percentage
    state, summary, metrics = results[3]
    assert state == 0  # OK
    assert "Used idle percentage: 1.00%" in summary
    assert metrics == []


def test_postgres_connections_check_app_test_warning() -> None:
    """Test check function for app_test database with warning levels."""
    params = {"levels_perc_active": (80.0, 90.0), "levels_perc_idle": (1.0, 5.0)}

    results = list(check_postgres_connections("app_test", params, parsed()))

    assert len(results) == 4

    # Check idle percentage (should be warning)
    state, summary, metrics = results[3]
    assert state == 1  # WARNING
    assert "Used idle percentage: 2.00%" in summary
    assert "warn/crit at 1.00%/5.00%" in summary
    assert metrics == []


def test_postgres_connections_check_postgres_critical() -> None:
    """Test check function for postgres database with critical levels."""
    params = {
        "levels_perc_active": (80.0, 90.0),
        "levels_perc_idle": (80.0, 90.0),
        "levels_abs_active": (2, 5),
    }

    results = list(check_postgres_connections("postgres", params, parsed()))

    assert len(results) == 4

    # Check active connections (should be critical)
    state, summary, metrics = results[0]
    assert state == 2  # CRITICAL
    assert "Used active connections: 9" in summary
    assert "warn/crit at 2/5" in summary
    assert metrics == [("active_connections", 9.0, 2, 5, 0, 100.0)]


def test_postgres_connections_check_missing_item() -> None:
    """Test check function for missing database item."""
    params = {"levels_perc_active": (80.0, 90.0), "levels_perc_idle": (80.0, 90.0)}

    with pytest.raises(IgnoreResultsError):
        list(check_postgres_connections("nonexistent", params, parsed()))
