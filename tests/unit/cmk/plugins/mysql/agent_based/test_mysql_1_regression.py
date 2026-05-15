#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.mysql.agent_based import mysql


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

    return mysql.parse_mysql(string_table)


def test_mysql_version_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    discovery_func = mysql._discover_keys({"version"})
    result = list(discovery_func(parsed))
    assert result == [Service(item="mysql")]


def test_mysql_version_check(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    result = list(mysql.check_mysql_version("mysql", parsed))
    assert result == [Result(state=State.OK, summary="Version: Cheesgrater Edition")]


def test_mysql_sessions_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    result = list(mysql.discover_mysql_sessions(parsed))
    assert result == [Service(item="mysql")]


def test_mysql_sessions_check(
    parsed: Mapping[str, Mapping[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store to avoid GetRateError
    value_store: dict[str, object] = {"mysql.sessions": (0, 2)}
    monkeypatch.setattr(mysql, "get_value_store", lambda: value_store)

    result = list(mysql.check_mysql_sessions("mysql", {}, parsed))

    # 3 sub-checks × (Result + Metric) = 6 items
    assert len(result) == 6

    # Results at indexes 0, 2, 4; metrics at 1, 3, 5
    assert isinstance(result[0], Result)
    assert result[0].state == State.OK
    assert "3 total" in result[0].summary
    assert isinstance(result[1], Metric)
    assert result[1].name == "total_sessions"
    assert result[1].value == 3.0

    assert isinstance(result[2], Result)
    assert result[2].state == State.OK
    assert "23 running" in result[2].summary
    assert isinstance(result[3], Metric)
    assert result[3].name == "running_sessions"
    assert result[3].value == 23.0

    assert isinstance(result[4], Result)
    assert result[4].state == State.OK
    assert "connections/s" in result[4].summary
    assert isinstance(result[5], Metric)
    assert result[5].name == "connect_rate"


def test_mysql_connections_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    discovery_func = mysql._discover_keys(
        {"Max_used_connections", "max_connections", "Threads_connected"}
    )
    result = list(discovery_func(parsed))
    assert result == [Service(item="mysql")]


def test_mysql_connections_check(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    params = {"perc_used": (75, 80), "perc_conn_threads": (40, 50)}
    result = list(mysql.check_mysql_connections("mysql", params, parsed))

    # First Result + Metric for perc_used, then 2 raw Metrics, then Result + Metric for perc_conn_threads, then 1 metric
    # Total = 2 + 2 + 2 + 1 = 7 entries
    assert len(result) == 7

    assert isinstance(result[0], Result)
    assert result[0].state == State.OK
    assert "Max. parallel connections since server start: 50.00%" in result[0].summary
    assert isinstance(result[1], Metric)
    assert result[1].name == "connections_perc_used"
    assert result[1].value == 50.0

    # 2 raw metrics: connections_max_used and connections_max
    assert isinstance(result[2], Metric) and result[2].name == "connections_max_used"
    assert isinstance(result[3], Metric) and result[3].name == "connections_max"

    # Currently open: state CRIT (75% >= 50%)
    assert isinstance(result[4], Result)
    assert result[4].state == State.CRIT
    assert "Currently open connections: 75.00%" in result[4].summary
    assert isinstance(result[5], Metric)
    assert result[5].name == "connections_perc_conn_threads"
    assert result[5].value == 75.0

    assert isinstance(result[6], Metric) and result[6].name == "connections_conn_threads"


def test_mysql_innodb_io_discovery(parsed: Mapping[str, Mapping[str, Any]]) -> None:
    discovery_func = mysql._discover_keys({"Innodb_data_read"})
    result = list(discovery_func(parsed))
    assert result == [Service(item="mysql")]


def test_mysql_innodb_io_check(
    parsed: Mapping[str, Mapping[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store to avoid GetRateError
    value_store: dict[str, object] = {"read": (0.0, 1024), "write": (0.0, 2048)}
    monkeypatch.setattr(mysql, "get_value_store", lambda: value_store)

    result = list(mysql.check_mysql_iostat("mysql", {}, parsed))

    # For each direction (read, write): Result + Metric = 2 items each => 4 total
    assert len(result) == 4

    assert isinstance(result[0], Result)
    assert result[0].state == State.OK
    assert "Read: 0.00 B/s" in result[0].summary
    assert isinstance(result[1], Metric) and result[1].name == "read"

    assert isinstance(result[2], Result)
    assert result[2].state == State.OK
    assert "Write: 0.00 B/s" in result[2].summary
    assert isinstance(result[3], Metric) and result[3].name == "write"


def test_mysql_parse_function() -> None:
    string_table = [
        ["version", "Cheesgrater Edition"],
        ["Aborted_clients", "0"],
        ["Threads_connected", "3"],
        ["Connections", "2"],
        ["max_connections", "4"],
        ["Innodb_data_read", "1024"],
        ["Innodb_data_written", "2048"],
    ]

    result = mysql.parse_mysql(string_table)

    assert "mysql" in result
    mysql_data = result["mysql"]

    assert mysql_data["version"] == "Cheesgrater Edition"
    assert mysql_data["Aborted_clients"] == 0
    assert mysql_data["Threads_connected"] == 3
    assert mysql_data["Connections"] == 2
    assert mysql_data["max_connections"] == 4
    assert mysql_data["Innodb_data_read"] == 1024
    assert mysql_data["Innodb_data_written"] == 2048


def test_mysql_version_discovery_empty_section() -> None:
    discovery_func = mysql._discover_keys({"version"})
    result = list(discovery_func({}))
    assert result == []


def test_mysql_sessions_discovery_insufficient_data() -> None:
    small_parsed = {"mysql": {"version": "test", "Threads_connected": "3"}}
    result = list(mysql.discover_mysql_sessions(small_parsed))
    assert result == []
