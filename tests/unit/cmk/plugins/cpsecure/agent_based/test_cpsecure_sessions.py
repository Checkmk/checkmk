#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.cpsecure.agent_based import cpsecure_sessions

# service, enabled, number of sessions
STRING_TABLE: StringTable = [
    ["HTTP", "1", "1682"],
    ["SMTP", "1", "216"],
    ["POP3", "1", "0"],
    ["FTP", "1", "1"],
    ["HTTPS", "2", "0"],
    ["IMAP", "1", "48"],
]


def test_parse_keeps_the_string_table() -> None:
    assert cpsecure_sessions.parse_cpsecure_sessions(STRING_TABLE) == STRING_TABLE


def test_discover_only_enabled_services() -> None:
    """A disabled service has no sessions to count, so monitoring it would only produce a
    permanent warning."""
    assert list(cpsecure_sessions.discover_cpsecure_sessions(STRING_TABLE)) == [
        Service(item="HTTP"),
        Service(item="SMTP"),
        Service(item="POP3"),
        Service(item="FTP"),
        Service(item="IMAP"),
    ]


def test_discover_without_any_service() -> None:
    assert list(cpsecure_sessions.discover_cpsecure_sessions([])) == []


@pytest.mark.parametrize(
    "item,sessions,expected_state",
    [
        pytest.param("POP3", "0", State.OK, id="no_sessions"),
        pytest.param("HTTP", "1682", State.OK, id="below_the_levels"),
        pytest.param("HTTP", "2499", State.OK, id="just_below_the_warn_level"),
        pytest.param("HTTP", "2500", State.WARN, id="at_the_warn_level"),
        pytest.param("HTTP", "4999", State.WARN, id="just_below_the_crit_level"),
        pytest.param("HTTP", "5000", State.CRIT, id="at_the_crit_level"),
    ],
)
def test_check_applies_the_fixed_session_levels(
    item: str, sessions: str, expected_state: State
) -> None:
    section: StringTable = [[item, "1", sessions]]

    results = list(cpsecure_sessions.check_cpsecure_sessions(item, section))

    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].state is expected_state
    assert results[0].summary.startswith(f"Sessions: {sessions}")


def test_check_warns_about_a_service_that_was_disabled_after_discovery() -> None:
    assert list(cpsecure_sessions.check_cpsecure_sessions("HTTPS", STRING_TABLE)) == [
        Result(state=State.WARN, summary="service not enabled")
    ]


def test_check_only_looks_at_its_own_service() -> None:
    results = list(cpsecure_sessions.check_cpsecure_sessions("IMAP", STRING_TABLE))

    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].summary.startswith("Sessions: 48")


@pytest.mark.parametrize(
    "item,section",
    [
        pytest.param("TELNET", STRING_TABLE, id="service_vanished"),
        pytest.param("HTTP", [], id="empty_section"),
    ],
)
def test_check_of_a_missing_service_stays_silent(item: str, section: StringTable) -> None:
    assert list(cpsecure_sessions.check_cpsecure_sessions(item, section)) == []
