#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.oracle.agent_based.oracle_sessions import (
    check_oracle_sessions,
    discover_oracle_sessions,
    parse_oracle_sessions,
)


def test_discover_oracle_sessions_fail():
    assert not list(
        discover_oracle_sessions(parse_oracle_sessions([["foo", "FAILURE"], ["bar", "FAILURE"]]))
    )


_NORMAL = [["orcl", "97", "322", "105"]]
_FAILURE = [["orcl", "FAILURE", "ORA-00942: table or view does not exist"]]


def test_discover_oracle_sessions_normal():
    assert list(discover_oracle_sessions(parse_oracle_sessions(_NORMAL))) == [Service(item="orcl")]


def test_discover_oracle_sessions_skips_failure_only():
    assert not list(discover_oracle_sessions(parse_oracle_sessions(_FAILURE)))


def test_check_oracle_sessions_normal():
    result = list(
        check_oracle_sessions("orcl", {"sessions_abs": (150, 300)}, parse_oracle_sessions(_NORMAL))
    )
    assert result[0] == Result(state=State.OK, summary="Sessions: 97")


def test_check_oracle_sessions_surfaces_failure():
    assert list(
        check_oracle_sessions("orcl", {"sessions_abs": (150, 300)}, parse_oracle_sessions(_FAILURE))
    ) == [Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")]


def test_check_oracle_sessions_surfaces_non_ora_failure():
    failure = [
        ["orcl", "FAILURE", "IO Error: The Network Adapter could not establish the connection"]
    ]
    assert list(
        check_oracle_sessions("orcl", {"sessions_abs": (150, 300)}, parse_oracle_sessions(failure))
    ) == [
        Result(
            state=State.UNKNOWN,
            summary="IO Error: The Network Adapter could not establish the connection",
        )
    ]


_LEGACY_ERROR = [["orcl", "ORA-01017:", "invalid username/password"]]


def test_discover_oracle_sessions_skips_legacy_error():
    assert not list(discover_oracle_sessions(parse_oracle_sessions(_LEGACY_ERROR)))


def test_check_oracle_sessions_surfaces_legacy_error():
    assert list(
        check_oracle_sessions(
            "orcl", {"sessions_abs": (150, 300)}, parse_oracle_sessions(_LEGACY_ERROR)
        )
    ) == [
        Result(
            state=State.UNKNOWN,
            summary='Found error in agent output "ORA-01017: invalid username/password"',
        )
    ]
