#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for EC query filter operators."""

import pytest

from cmk.ec.main import EventStatus, StatusServer
from cmk.ec.query import MKClientError

from .helpers import new_event, query_status_server


def _selects(
    event_status: EventStatus, status_server: StatusServer, value: str, filter_spec: str
) -> bool:
    """Whether the filter on the text of an event selects the event with the value as text"""
    event_status.new_event(new_event({"text": value}))
    _header, *rows = query_status_server(
        status_server, f"GET events\nColumns: event_text\nFilter: event_text {filter_spec}"
    ).get_response()
    return value in {text for (text,) in rows}


def test_tilde_tilde_lowercase_pattern_matches_mixed_case_value(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "Hello World", "~~ hello") is True


def test_tilde_tilde_lowercase_pattern_matches_uppercase_value(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "HELLO WORLD", "~~ hello") is True


def test_tilde_tilde_uppercase_pattern_matches_lowercase_value(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "hello world", "~~ HELLO") is True


def test_tilde_tilde_regex_with_mixed_case_components(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "FooBar", "~~ foo.*bar") is True


def test_tilde_tilde_no_match(event_status: EventStatus, status_server: StatusServer) -> None:
    assert _selects(event_status, status_server, "hello", "~~ xyz") is False


def test_tilde_tilde_anchored_pattern_matches_lowercase_start(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "Hello", "~~ ^he") is True


def test_tilde_tilde_differs_from_case_sensitive_tilde(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    case_sensitive = _selects(event_status, status_server, "Hello", "~ hello")
    case_insensitive = _selects(event_status, status_server, "Hello", "~~ hello")

    assert case_sensitive is False
    assert case_insensitive is True


def test_tilde_tilde_keeps_the_meaning_of_uppercase_regex_escapes(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "Disk full", r"~~ ^\S+ full$") is True


def test_eq_tilde_differs_only_in_case(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "Hello", "=~ hello") is True


def test_eq_tilde_all_uppercase_equals_all_lowercase(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "HELLO", "=~ hello") is True


def test_eq_tilde_different_strings_do_not_match(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    assert _selects(event_status, status_server, "hello", "=~ world") is False


@pytest.mark.parametrize(
    "operator_name, value, argument, expected",
    [
        pytest.param("!=",  "Hello", "Hello", False, id="not equal, same value"),
        pytest.param("!=",  "Hello", "hello", True,  id="not equal, value differs in case"),
        pytest.param("!=~", "Hello", "hello", False, id="not equal ignoring case, value differs in case"),
        pytest.param("!=~", "Hello", "world", True,  id="not equal ignoring case, different value"),
        pytest.param("!~",  "Hello", "^He",   False, id="regex does not match, matching value"),
        pytest.param("!~",  "Hello", "^he",   True,  id="regex does not match, value differs in case"),
        pytest.param("!~~", "Hello", "^he",   False, id="regex does not match ignoring case, value differs in case"),
        pytest.param("!~~", "Hello", "^wo",   True,  id="regex does not match ignoring case, non-matching value"),
    ],
)  # fmt: skip
def test_negated_operator_holds_only_if_the_value_does_not_match(
    event_status: EventStatus,
    status_server: StatusServer,
    operator_name: str,
    value: str,
    argument: str,
    expected: bool,
) -> None:
    assert _selects(event_status, status_server, value, f"{operator_name} {argument}") is expected


def test_unknown_operator_raises(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Invalid header line") as excinfo:
        query_status_server(status_server, "GET events\nFilter: event_text ?? x")

    assert "Unknown filter operator" in str(excinfo.value.__cause__)
