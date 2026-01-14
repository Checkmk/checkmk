#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Pattern 5: Standalone test with embedded test data for PostgreSQL connection monitoring."""

from cmk.base.legacy_checks.postgres_connections import (
    check_postgres_connections,
    discover_postgres_connections,
)
from cmk.plugins.postgres.lib import parse_dbs


def test_postgres_connection_old_discovery():
    """Test discovery of PostgreSQL connection databases."""
    # Pattern 5d: Database monitoring data
    string_table = [
        ["[databases_start]"],
        ["postgres"],
        ["adwebconnect"],
        ["[databases_end]"],
        ["current", "mc", "datname"],
        ["1", "100", "postgres"],
    ]

    parsed = parse_dbs(string_table)
    result = list(discover_postgres_connections(parsed))

    # Should discover both databases
    assert len(result) == 2
    assert ("adwebconnect", {}) in result
    assert ("postgres", {}) in result


def test_postgres_connection_old_check_adwebconnect():
    """Test PostgreSQL connection check for adwebconnect database."""
    # Pattern 5d: Database monitoring data
    string_table = [
        ["[databases_start]"],
        ["postgres"],
        ["adwebconnect"],
        ["[databases_end]"],
        ["current", "mc", "datname"],
        ["1", "100", "postgres"],
    ]

    parsed = parse_dbs(string_table)
    params = {"levels_perc": (80.0, 90.0)}

    results = list(check_postgres_connections("adwebconnect", params, parsed))

    # Should report no active and idle connections for adwebconnect
    assert len(results) == 2
    assert results[0][0] == 0  # OK state
    assert "No active connections" in results[0][1]
    assert results[1][0] == 0  # OK state
    assert "No idle connections" in results[1][1]


def test_postgres_connection_old_check_postgres():
    """Test PostgreSQL connection check for postgres database."""
    # Pattern 5d: Database monitoring data
    string_table = [
        ["[databases_start]"],
        ["postgres"],
        ["adwebconnect"],
        ["[databases_end]"],
        ["current", "mc", "datname"],
        ["1", "100", "postgres"],
    ]

    parsed = parse_dbs(string_table)
    params = {"levels_perc": (80.0, 90.0)}

    results = list(check_postgres_connections("postgres", params, parsed))

    # Should report no active and idle connections for postgres too (since no data for adwebconnect)
    assert len(results) == 2
    assert results[0][0] == 0  # OK state
    assert "No active connections" in results[0][1]
    assert results[1][0] == 0  # OK state
    assert "No idle connections" in results[1][1]
