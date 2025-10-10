#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import get_value_store
from cmk.base.legacy_checks.mysql import (
    _discover_keys,
    check_mysql_connections,
    check_mysql_iostat,
    check_mysql_sessions,
    check_mysql_version,
    discover_mysql_sessions,
    parse_mysql,
)


@pytest.fixture
def parsed() -> Mapping[str, Mapping[str, Any]]:
    """Create parsed MySQL data using actual parse function."""
    string_table = [
        ["[[mysql]]"],
        ["version", "Cheesgrater Edition"],
        ["Aborted_clients", "0"],
        ["Aborted_connects", "15"],
        ["Binlog_cache_disk_use", "0"],
        ["Binlog_cache_use", "0"],
        ["Binlog_stmt_cache_disk_use", "0"],
        ["Binlog_stmt_cache_use", "0"],
        ["Bytes_received", "7198841"],
        ["Bytes_sent", "19266624"],
        ["Com_admin_commands", "200"],
        ["Com_assign_to_keycache", "0"],
        ["Com_alter_db", "0"],
        ["Com_alter_db_upgrade", "0"],
        ["Threads_connected", "3"],
        ["Connections", "2"],
        ["Threads_running", "23"],
        ["Innodb_data_read", "1024"],
        ["Innodb_data_written", "2048"],
        ["Max_used_connections", "2"],
        ["max_connections", "4"],
        # Add many more entries to trigger sessions discovery (needs > 200 entries)
        *[[str(i), str(i)] for i in range(200)],
    ]

    return parse_mysql(string_table)


def test_mysql_version_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL version discovery function."""
    discovery_func = _discover_keys({"version"})
    result = list(discovery_func(parsed))

    # Should discover exactly one service
    assert len(result) == 1
    assert result[0] == ("mysql", {})


def test_mysql_version_check(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL version check function."""
    result = list(check_mysql_version("mysql", {}, parsed))

    # Should have exactly one result
    assert len(result) == 1

    state, summary = result[0]
    assert state == 0
    assert "Version: Cheesgrater Edition" in summary


def test_mysql_sessions_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL sessions discovery function."""
    result = list(discover_mysql_sessions(parsed))

    # Should discover exactly one service (data has > 200 entries)
    assert len(result) == 1
    assert result[0] == ("mysql", {})


@pytest.mark.usefixtures("initialised_item_state")
def test_mysql_sessions_check(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL sessions check function."""
    # Pre-populate value store to avoid GetRateError
    get_value_store()["mysql.sessions"] = (0, 2)

    result = list(check_mysql_sessions("mysql", {}, parsed))

    # Should have exactly 3 results (total, running, connections rate)
    assert len(result) == 3

    # Check total sessions result
    state, summary, metrics = result[0]
    assert state == 0
    assert "3 total" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "total_sessions"
    assert metrics[0][1] == 3

    # Check running sessions result
    state, summary, metrics = result[1]
    assert state == 0
    assert "23 running" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "running_sessions"
    assert metrics[0][1] == 23

    # Check connections rate result
    state, summary, metrics = result[2]
    assert state == 0
    assert "connections/s" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "connect_rate"


def test_mysql_connections_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL connections discovery function."""
    discovery_func = _discover_keys(
        {"Max_used_connections", "max_connections", "Threads_connected"}
    )
    result = list(discovery_func(parsed))

    # Should discover exactly one service
    assert len(result) == 1
    assert result[0] == ("mysql", {})


def test_mysql_connections_check(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL connections check function."""
    params = {"perc_used": (75, 80), "perc_conn_threads": (40, 50)}
    result = list(check_mysql_connections("mysql", params, parsed))

    # Should have exactly 5 results
    assert len(result) == 5

    # Check max parallel connections result
    state, summary, metrics = result[0]
    assert state == 0
    assert "Max. parallel connections since server start: 50.00%" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "connections_perc_used"
    assert metrics[0][1] == 50.0

    # Check current connections result (should be critical)
    state, summary, metrics = result[3]
    assert state == 2
    assert "Currently open connections: 75.00%" in summary
    assert "(warn/crit at 40.00%/50.00%)" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "connections_perc_conn_threads"
    assert metrics[0][1] == 75.0


def test_mysql_innodb_io_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL InnoDB I/O discovery function."""
    discovery_func = _discover_keys({"Innodb_data_read"})
    result = list(discovery_func(parsed))

    # Should discover exactly one service
    assert len(result) == 1
    assert result[0] == ("mysql", {})


@pytest.mark.usefixtures("initialised_item_state")
def test_mysql_innodb_io_check(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    """Test MySQL InnoDB I/O check function."""
    # Pre-populate value store to avoid GetRateError
    get_value_store()["read"] = (0.0, 1024)
    get_value_store()["write"] = (0.0, 2048)

    result = list(check_mysql_iostat("mysql", {}, parsed))

    # Should have exactly 3 results (read, write, perfdata)
    assert len(result) == 3

    # Check read result
    state, summary = result[0][:2]
    assert state == 0
    assert "Read: 0.00 B/s" in summary

    # Check write result
    state, summary = result[1][:2]
    assert state == 0
    assert "Write: 0.00 B/s" in summary

    # Check perfdata result
    state, summary, metrics = result[2]
    assert state == 0
    assert len(metrics) == 2
    assert metrics[0][0] == "read"
    assert metrics[1][0] == "write"


def test_mysql_parse_function() -> None:
    """Test MySQL parse function with the exact dataset."""
    string_table = [
        ["version", "Cheesgrater Edition"],
        ["Aborted_clients", "0"],
        ["Threads_connected", "3"],
        ["Connections", "2"],
        ["max_connections", "4"],
        ["Innodb_data_read", "1024"],
        ["Innodb_data_written", "2048"],
    ]

    result = parse_mysql(string_table)

    # Should parse exactly one MySQL instance
    assert "mysql" in result
    mysql_data = result["mysql"]

    # Check parsed values
    assert mysql_data["version"] == "Cheesgrater Edition"
    assert mysql_data["Aborted_clients"] == 0
    assert mysql_data["Threads_connected"] == 3
    assert mysql_data["Connections"] == 2
    assert mysql_data["max_connections"] == 4
    assert mysql_data["Innodb_data_read"] == 1024
    assert mysql_data["Innodb_data_written"] == 2048


def test_mysql_version_discovery_empty_section() -> None:
    """Test MySQL version discovery function with empty section."""
    discovery_func = _discover_keys({"version"})
    result = list(discovery_func({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_mysql_sessions_discovery_insufficient_data() -> None:
    """Test MySQL sessions discovery function with insufficient data."""
    # Create parsed data with < 200 entries
    small_parsed = {"mysql": {"version": "test", "Threads_connected": "3"}}
    result = list(discover_mysql_sessions(small_parsed))

    # Should not discover any service with insufficient data
    assert len(result) == 0
