#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.mysql_ping import (
    check_mysql_ping,
    discover_mysql_ping,
    parse_mysql_ping,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for MySQL ping with multiple instances"""
    return [
        ["this", "line", "is", "no", "longer", "ignored"],
        ["[[elephant]]"],
        ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
        ["[[moth]]"],
        ["mysqld", "is", "alive"],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> Mapping[str, Any]:
    """Parsed MySQL ping data"""
    return parse_mysql_ping(string_table)


def test_discover_mysql_ping(parsed: Mapping[str, Any]) -> None:
    """Test MySQL ping discovery finds all instances"""
    discovered = list(discover_mysql_ping(parsed))
    assert len(discovered) == 3

    # Should discover all instances
    instance_names = [item[0] for item in discovered]
    assert "mysql" in instance_names
    assert "elephant" in instance_names
    assert "moth" in instance_names

    # All should have empty parameters
    for _, params in discovered:
        assert params == {}


def test_check_mysql_ping_alive_instance(parsed: Mapping[str, Any]) -> None:
    """Test MySQL ping check for alive instance"""
    result = list(check_mysql_ping("moth", {}, parsed))
    assert len(result) == 1

    state, message = result[0]
    assert state == 0  # OK
    assert message == "MySQL Daemon is alive"


def test_check_mysql_ping_connection_failed(parsed: Mapping[str, Any]) -> None:
    """Test MySQL ping check for connection failure"""
    result = list(check_mysql_ping("elephant", {}, parsed))
    assert len(result) == 1

    state, message = result[0]
    assert state == 2  # CRITICAL
    assert message == "mysqladmin: connect to server at 'localhost' failed"


def test_check_mysql_ping_error_message(parsed: Mapping[str, Any]) -> None:
    """Test MySQL ping check for generic error message"""
    result = list(check_mysql_ping("mysql", {}, parsed))
    assert len(result) == 1

    state, message = result[0]
    assert state == 2  # CRITICAL
    assert message == "this line is no longer ignored"


def test_check_mysql_ping_missing_instance(parsed: Mapping[str, Any]) -> None:
    """Test MySQL ping check for non-existent instance"""
    result = list(check_mysql_ping("nonexistent", {}, parsed))
    assert len(result) == 0  # No results for missing instance


def test_parse_mysql_ping(string_table: list[list[str]]) -> None:
    """Test MySQL ping parsing creates proper instance mapping"""
    parsed = parse_mysql_ping(string_table)

    # Should have 3 instances
    assert len(parsed) == 3
    assert "mysql" in parsed
    assert "elephant" in parsed
    assert "moth" in parsed

    # Check instance data content
    assert parsed["mysql"] == [["this", "line", "is", "no", "longer", "ignored"]]
    assert parsed["elephant"] == [
        ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"]
    ]
    assert parsed["moth"] == [["mysqld", "is", "alive"]]


def test_check_mysql_ping_different_alive_message() -> None:
    """Test MySQL ping with standard alive message format"""
    simple_data = [
        ["[[test_instance]]"],
        ["mysqld", "is", "alive"],
    ]

    parsed = parse_mysql_ping(simple_data)
    result = list(check_mysql_ping("test_instance", {}, parsed))

    assert len(result) == 1
    state, message = result[0]
    assert state == 0  # OK
    assert message == "MySQL Daemon is alive"


def test_check_mysql_ping_access_denied_error() -> None:
    """Test MySQL ping with access denied error"""
    error_data = [
        ["[[secure_db]]"],
        [
            "error:",
            "'Access",
            "denied",
            "for",
            "user",
            "'root'@'localhost'",
            "(using",
            "password:",
            "NO)'",
        ],
    ]

    parsed = parse_mysql_ping(error_data)
    result = list(check_mysql_ping("secure_db", {}, parsed))

    assert len(result) == 1
    state, message = result[0]
    assert state == 2  # CRITICAL
    assert message == "error: 'Access denied for user 'root'@'localhost' (using password: NO)'"
