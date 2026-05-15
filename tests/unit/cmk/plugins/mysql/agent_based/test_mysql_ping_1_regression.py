#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.mysql.agent_based.mysql_ping import (
    check_mysql_ping,
    discover_mysql_ping,
    parse_mysql_ping,
    Section,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    return [
        ["this", "line", "is", "no", "longer", "ignored"],
        ["[[elephant]]"],
        ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
        ["[[moth]]"],
        ["mysqld", "is", "alive"],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> Section:
    return parse_mysql_ping(string_table)


def test_discover_mysql_ping(parsed: Section) -> None:
    discovered = list(discover_mysql_ping(parsed))
    assert len(discovered) == 3
    instance_names = [s.item for s in discovered]
    assert "mysql" in instance_names
    assert "elephant" in instance_names
    assert "moth" in instance_names


def test_check_mysql_ping_alive_instance(parsed: Section) -> None:
    result = list(check_mysql_ping("moth", parsed))
    assert result == [Result(state=State.OK, summary="MySQL Daemon is alive")]


def test_check_mysql_ping_connection_failed(parsed: Section) -> None:
    result = list(check_mysql_ping("elephant", parsed))
    assert result == [
        Result(state=State.CRIT, summary="mysqladmin: connect to server at 'localhost' failed")
    ]


def test_check_mysql_ping_error_message(parsed: Section) -> None:
    result = list(check_mysql_ping("mysql", parsed))
    assert result == [Result(state=State.CRIT, summary="this line is no longer ignored")]


def test_check_mysql_ping_missing_instance(parsed: Section) -> None:
    result = list(check_mysql_ping("nonexistent", parsed))
    assert result == []


def test_parse_mysql_ping(string_table: list[list[str]]) -> None:
    parsed = parse_mysql_ping(string_table)

    assert len(parsed) == 3
    assert "mysql" in parsed
    assert "elephant" in parsed
    assert "moth" in parsed

    assert parsed["mysql"] == [["this", "line", "is", "no", "longer", "ignored"]]
    assert parsed["elephant"] == [
        ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"]
    ]
    assert parsed["moth"] == [["mysqld", "is", "alive"]]


def test_check_mysql_ping_different_alive_message() -> None:
    simple_data = [
        ["[[test_instance]]"],
        ["mysqld", "is", "alive"],
    ]

    parsed = parse_mysql_ping(simple_data)
    result = list(check_mysql_ping("test_instance", parsed))
    assert result == [Result(state=State.OK, summary="MySQL Daemon is alive")]


def test_check_mysql_ping_access_denied_error() -> None:
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
    result = list(check_mysql_ping("secure_db", parsed))
    assert result == [
        Result(
            state=State.CRIT,
            summary="error: 'Access denied for user 'root'@'localhost' (using password: NO)'",
        )
    ]
