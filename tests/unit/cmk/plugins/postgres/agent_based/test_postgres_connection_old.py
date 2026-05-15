#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Pattern 5: Standalone test with embedded test data for PostgreSQL connection monitoring."""

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.postgres.agent_based.postgres_connections import (
    check_postgres_connections,
    discover_postgres_connections,
)
from cmk.plugins.postgres.lib import parse_dbs


def test_postgres_connection_old_discovery() -> None:
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

    assert len(result) == 2
    assert Service(item="adwebconnect") in result
    assert Service(item="postgres") in result


def test_postgres_connection_old_check_adwebconnect() -> None:
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

    # No active and idle: each yields Result + Metric = 4 items total
    assert len(results) == 4
    assert isinstance(results[0], Result) and results[0].state == State.OK
    assert "No active connections" in results[0].summary
    assert isinstance(results[2], Result) and results[2].state == State.OK
    assert "No idle connections" in results[2].summary


def test_postgres_connection_old_check_postgres() -> None:
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

    # No active and idle: each yields Result + Metric = 4 items total
    assert len(results) == 4
    assert isinstance(results[0], Result) and results[0].state == State.OK
    assert "No active connections" in results[0].summary
    assert isinstance(results[2], Result) and results[2].state == State.OK
    assert "No idle connections" in results[2].summary
