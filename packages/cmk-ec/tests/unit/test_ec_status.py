#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.main import EventStatus, StatusServer, StatusTableEvents
from cmk.ec.query import MKClientError

from .helpers import (
    EVENTS_WITH_CONTACT_GROUPS,
    EVENTS_WITH_FIRST_TIMES,
    FakeStatusSocket,
    LIST_FILTER_CASES,
    new_event,
    query_status_server,
    TIME_FILTER_CASES,
)


def test_handle_client(status_server: StatusServer) -> None:
    s = FakeStatusSocket(b"GET events")

    status_server.handle_client(s, True, "127.0.0.1")

    response = s.get_response()
    assert len(response) == 1
    assert "event_id" in response[0]


@pytest.mark.usefixtures("config")
def test_mkevent_check_query_perf(event_status: EventStatus, status_server: StatusServer) -> None:
    for num in range(10000):
        event_status.new_event(
            new_event(
                {
                    "host": HostName(f"heute-{num}"),
                    "text": f"{time.time()} {num} BLA BLUB DINGELING ABASD AD R#@A AR@AR A@ RA@R A@RARAR ARKNLA@RKA@LRKNA@KRLNA@RLKNA@äRLKA@RNKAL@R"
                    " j:O#A@J$ KLA@J $L:A@J :AMW: RAMR@: RMA@:LRMA@ L:RMA@ :AL@R MA:L@RM A@:LRMA@ :RLMA@ R:LA@RMM@RL:MA@R: AM@",
                    "core_host": HostName(f"heute-{num}"),
                }
            )
        )

    assert len(event_status.events()) == 10000

    s = FakeStatusSocket(
        b"GET events\n"
        b"Filter: event_host in heute-1 127.0.0.1 heute123\n"
        b"Filter: event_phase in open ack\n"
    )

    before = time.time()

    status_server.handle_client(s, True, "127.0.0.1")

    duration = time.time() - before

    response = s.get_response()
    assert len(response) == 2
    assert "event_id" in response[0]

    assert duration < 0.2


@pytest.mark.parametrize(
    "event, status_socket, is_match",
    [
        (
            {
                "host": "abc",
                "text": "not important",
                "core_host": "abc",
            },
            FakeStatusSocket(
                b"GET events\n"
                b"Filter: event_host in abc 127.0.0.1\n"
                b"Filter: event_phase in open ack\n"
            ),
            True,
        ),
        (
            {
                "host": "127.0.0.1",
                "text": "not important",
                "core_host": "127.0.0.1",
            },
            FakeStatusSocket(
                b"GET events\n"
                b"Filter: event_host in abc 127.0.0.1\n"
                b"Filter: event_phase in open ack\n"
            ),
            True,
        ),
        (
            {
                "host": "ABC",
                "text": "not important",
                "core_host": "ABC",
            },
            FakeStatusSocket(
                b"GET events\n"
                b"Filter: event_host in abc 127.0.0.1\n"
                b"Filter: event_phase in open ack\n"
            ),
            True,
        ),
        (
            {
                "host": "ABC1",
                "text": "not important",
                "core_host": "ABC",
            },
            FakeStatusSocket(
                b"GET events\n"
                b"Filter: event_host in abc 127.0.0.1\n"
                b"Filter: event_phase in open ack\n"
            ),
            False,
        ),
    ],
)
def test_mkevent_query_filters(
    event_status: EventStatus,
    status_server: StatusServer,
    event: ec.Event,
    status_socket: FakeStatusSocket,
    is_match: bool,
) -> None:
    event_status.new_event(new_event(event))
    status_server.handle_client(status_socket, True, "127.0.0.1")
    response = status_socket.get_response()
    assert (len(response) == 2) is is_match


def query_texts_of_events(status_server: StatusServer, filter_line: str) -> set[str]:
    status_socket = FakeStatusSocket(f"GET events\nColumns: event_text\n{filter_line}\n".encode())
    status_server.handle_client(status_socket, True, "127.0.0.1")
    _header, *rows = status_socket.get_response()
    return {text for (text,) in rows}


@pytest.mark.parametrize(
    "operator_name",
    [
        pytest.param("=", id="equal"),
        pytest.param("=~", id="equal ignoring case"),
        pytest.param("~", id="regex matches"),
        pytest.param("~~", id="regex matches ignoring case"),
        pytest.param("in", id="in"),
    ],
)
def test_filter_does_not_select_events_without_a_value(
    event_status: EventStatus, status_server: StatusServer, operator_name: str
) -> None:
    event_status.new_event(new_event({"text": "unknown", "core_host": None}))
    event_status.new_event(new_event({"text": "mine", "core_host": HostName("myhost")}))
    event_status.new_event(new_event({"text": "other", "core_host": HostName("otherhost")}))

    texts = query_texts_of_events(status_server, f"Filter: event_core_host {operator_name} myhost")

    assert texts == {"mine"}


@pytest.mark.parametrize(
    "operator_name",
    [
        pytest.param("!=", id="not equal"),
        pytest.param("!=~", id="not equal ignoring case"),
        pytest.param("!~", id="regex does not match"),
        pytest.param("!~~", id="regex does not match ignoring case"),
    ],
)
def test_negated_filter_selects_events_without_a_value(
    event_status: EventStatus, status_server: StatusServer, operator_name: str
) -> None:
    event_status.new_event(new_event({"text": "unknown", "core_host": None}))
    event_status.new_event(new_event({"text": "mine", "core_host": HostName("myhost")}))
    event_status.new_event(new_event({"text": "other", "core_host": HostName("otherhost")}))

    texts = query_texts_of_events(status_server, f"Filter: event_core_host {operator_name} myhost")

    assert texts == {"unknown", "other"}


# Like NULL in SQL, a missing value isn't ordered, so even "!<", i.e. ">=", doesn't select it.
@pytest.mark.parametrize(
    "operator_name, expected_texts",
    [
        pytest.param("<",   {"mine"},  id="less"),
        pytest.param("<=",  {"mine"},  id="less or equal"),
        pytest.param(">",   {"other"}, id="greater"),
        pytest.param(">=",  {"other"}, id="greater or equal"),
        pytest.param("!<",  {"other"}, id="not less"),
        pytest.param("!<=", {"other"}, id="not less or equal"),
        pytest.param("!>",  {"mine"},  id="not greater"),
        pytest.param("!>=", {"mine"},  id="not greater or equal"),
    ],
)  # fmt: skip
def test_ordering_filter_does_not_select_events_without_a_value(
    event_status: EventStatus,
    status_server: StatusServer,
    operator_name: str,
    expected_texts: set[str],
) -> None:
    event_status.new_event(new_event({"text": "unknown", "core_host": None}))
    event_status.new_event(new_event({"text": "mine", "core_host": HostName("myhost")}))
    event_status.new_event(new_event({"text": "other", "core_host": HostName("otherhost")}))

    texts = query_texts_of_events(status_server, f"Filter: event_core_host {operator_name} n")

    assert texts == expected_texts


def test_filter_compares_the_default_of_a_column_missing_in_an_event(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "without owner"}))
    event_status.new_event(new_event({"text": "with owner", "owner": "admin"}))

    texts = query_texts_of_events(status_server, "Filter: event_owner =")

    assert texts == {"without owner"}


@pytest.mark.parametrize(
    "line_boundary",
    [
        pytest.param("\r", id="carriage return"),
        pytest.param("\v", id="vertical tab"),
        pytest.param("\x1c", id="file separator"),
        pytest.param("\x85", id="next line"),
        pytest.param("\u2028", id="line separator"),
        pytest.param("\u2029", id="paragraph separator"),
    ],
)
def test_only_a_newline_ends_a_header_line(
    event_status: EventStatus, status_server: StatusServer, line_boundary: str
) -> None:
    text = f"a{line_boundary}Limit: 0"
    event_status.new_event(new_event({"text": text}))

    texts = query_texts_of_events(status_server, f"Filter: event_text = {text}")

    assert texts == {text}


@pytest.mark.parametrize(
    "whitespace",
    [
        pytest.param("\x1c", id="file separator"),
        pytest.param("\x85", id="next line"),
        pytest.param("\xa0", id="no-break space"),
        pytest.param("\u2028", id="line separator"),
    ],
)
def test_filter_value_keeps_what_only_python_takes_as_whitespace(
    event_status: EventStatus, status_server: StatusServer, whitespace: str
) -> None:
    event_status.new_event(new_event({"text": f"{whitespace}x{whitespace}"}))
    event_status.new_event(new_event({"text": "x"}))

    texts = query_texts_of_events(status_server, f"Filter: event_text = {whitespace}x{whitespace}")

    assert texts == {f"{whitespace}x{whitespace}"}


@pytest.mark.parametrize(
    "filter_line",
    [
        pytest.param("Filter: event_text = x", id="spaces"),
        pytest.param("Filter: event_text  =  x", id="several spaces"),
        pytest.param("Filter:\tevent_text\t=\tx", id="tabs"),
        pytest.param("Filter: event_text = \v\fx", id="other ASCII whitespace"),
    ],
)
def test_filter_line_is_split_at_ascii_whitespace_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, filter_line: str
) -> None:
    for text in ["x", " x", "\tx"]:
        event_status.new_event(new_event({"text": text}))

    texts = query_texts_of_events(status_server, filter_line)

    assert texts == {"x"}


@pytest.mark.parametrize(
    "whitespace",
    [
        pytest.param(" ", id="space"),
        pytest.param("\t", id="tab"),
        pytest.param("\v\f", id="other ASCII whitespace"),
    ],
)
def test_whitespace_at_the_end_of_a_line_is_dropped_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, whitespace: str
) -> None:
    event_status.new_event(new_event({"text": "x"}))
    event_status.new_event(new_event({"text": f"x{whitespace}"}))

    texts = query_texts_of_events(status_server, f"Filter: event_text = x{whitespace}")

    assert texts == {"x"}


def test_query_with_crlf_line_endings_is_understood(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "x"}))
    event_status.new_event(new_event({"text": "y"}))
    status_socket = FakeStatusSocket(
        b"GET events\r\nColumns: event_text\r\nFilter: event_text = x\r\n"
    )

    status_server.handle_client(status_socket, True, "127.0.0.1")

    assert status_socket.get_response() == [["event_text"], ["x"]]


def test_in_operator_splits_its_list_at_ascii_whitespace_only(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    for text in ["a\xa0b", "a", "b", "c"]:
        event_status.new_event(new_event({"text": text}))

    texts = query_texts_of_events(status_server, "Filter: event_text in a\xa0b\tc")

    assert texts == {"a\xa0b", "c"}


@pytest.mark.parametrize(
    "method_line",
    [
        pytest.param("GET\xa0events", id="no-break space"),
        pytest.param("GET\tevents", id="tab"),
    ],
)
def test_method_is_followed_by_a_space_like_in_livestatus(
    status_server: StatusServer, method_line: str
) -> None:
    with pytest.raises(MKClientError, match="Invalid query"):
        query_status_server(status_server, method_line)


def test_lines_with_only_whitespace_are_ignored_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "x"}))

    status_socket = query_status_server(status_server, "GET events\n \t\nColumns: event_text\n\v")

    assert status_socket.get_response() == [["event_text"], ["x"]]


def test_request_starting_with_an_empty_line_is_empty_like_in_livestatus(
    status_server: StatusServer,
) -> None:
    with pytest.raises(MKClientError, match="Invalid query"):
        query_status_server(status_server, "GET events\n\n\nGET status")


@pytest.mark.parametrize(
    "columns_line",
    [
        pytest.param("Columns: event_text event_host", id="space"),
        pytest.param("Columns:  event_text  event_host", id="several spaces"),
        pytest.param("Columns:\tevent_text\tevent_host", id="tabs"),
        pytest.param("Columns:\v\fevent_text\v\fevent_host", id="other ASCII whitespace"),
    ],
)
def test_columns_are_split_at_ascii_whitespace_like_in_livestatus(
    status_server: StatusServer, columns_line: str
) -> None:
    status_socket = query_status_server(status_server, f"GET events\n{columns_line}")

    assert status_socket.get_response() == [["event_text", "event_host"]]


def test_empty_columns_header_requests_all_columns_like_in_livestatus(
    status_server: StatusServer,
) -> None:
    status_socket = query_status_server(status_server, "GET events\nColumns:")

    assert status_socket.get_response() == [[name for name, _default in StatusTableEvents.columns]]


def test_columns_of_several_headers_add_up_like_in_livestatus(status_server: StatusServer) -> None:
    status_socket = query_status_server(
        status_server, "GET events\nColumns: event_text\nColumns:\nColumns: event_host"
    )

    assert status_socket.get_response() == [["event_text", "event_host"]]


def test_header_without_colon_has_no_argument_like_in_livestatus(
    status_server: StatusServer,
) -> None:
    status_socket = query_status_server(status_server, "GET events\nColumns")

    assert status_socket.get_response() == [[name for name, _default in StatusTableEvents.columns]]


@pytest.mark.parametrize(
    "output_format_line",
    [
        pytest.param("OutputFormat:\tplain", id="tab"),
        pytest.param("OutputFormat: plain python", id="further argument"),
    ],
)
def test_output_format_is_the_first_argument_like_in_livestatus(
    status_server: StatusServer, output_format_line: str
) -> None:
    status_socket = query_status_server(
        status_server, f"GET events\nColumns: event_text\n{output_format_line}"
    )

    assert status_socket.get_raw_response() == b"event_text\n"


@pytest.mark.parametrize(
    "limit_line",
    [
        pytest.param("Limit:\t1", id="tab"),
        pytest.param("Limit: 1 2", id="further argument"),
    ],
)
def test_limit_is_the_first_argument_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, limit_line: str
) -> None:
    for text in ["x", "y"]:
        event_status.new_event(new_event({"text": text}))

    texts = query_texts_of_events(status_server, limit_line)

    assert len(texts) == 1


@pytest.mark.parametrize(
    "limit",
    [
        pytest.param("-1", id="negative"),
        pytest.param("+1", id="plus sign"),
        pytest.param("1_000", id="underscore"),
        pytest.param("\xa01", id="no-break space"),
        pytest.param("١", id="arabic-indic digit"),
        pytest.param("2147483648", id="more than 31 bits"),
        pytest.param("9" * 5000, id="more digits than int() takes"),
    ],
)
def test_limit_is_a_non_negative_int_like_in_livestatus(
    status_server: StatusServer, limit: str
) -> None:
    with pytest.raises(MKClientError, match="Invalid header line"):
        query_status_server(status_server, f"GET events\nLimit: {limit}")


def test_limit_minus_zero_is_zero_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "x"}))

    texts = query_texts_of_events(status_server, "Limit: -0")

    assert texts == set()


def test_limit_with_more_digits_than_int_takes_is_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "x"}))
    event_status.new_event(new_event({"text": "y"}))

    texts = query_texts_of_events(status_server, f"Limit: {'0' * 5000}1")

    assert len(texts) == 1


@pytest.mark.parametrize(
    "operator_name, expected_texts",
    [
        pytest.param("!<", {"2", "3"}, id="not less"),
        pytest.param("!>=", {"1"}, id="not greater or equal"),
        pytest.param("!>", {"1", "2"}, id="not greater"),
        pytest.param("!<=", {"3"}, id="not less or equal"),
    ],
)
def test_negated_ordering_operators_are_aliases_like_in_livestatus(
    event_status: EventStatus,
    status_server: StatusServer,
    operator_name: str,
    expected_texts: set[str],
) -> None:
    for count in [1, 2, 3]:
        event_status.new_event(new_event({"text": str(count), "count": count}))

    texts = query_texts_of_events(status_server, f"Filter: event_count {operator_name} 2")

    assert texts == expected_texts


@pytest.mark.parametrize(
    "value, expected_count",
    [
        pytest.param("5abc", 5, id="trailing garbage"),
        pytest.param("abc", 0, id="no number"),
        pytest.param("1_000", 1, id="underscore"),
        pytest.param("١", 0, id="arabic-indic digit"),
        pytest.param("99999999999", 1215752191, id="more than 32 bits"),
        pytest.param("-99999999999", -1215752191, id="more than 32 bits, negative"),
        pytest.param("9" * 5000, -1, id="more digits than int() takes"),
        pytest.param("0" * 5000 + "5", 5, id="more leading zeros than int() takes"),
    ],
)
def test_int_filter_value_is_parsed_like_atoi_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, value: str, expected_count: int
) -> None:
    for count in [-1215752191, -1, 0, 1, 5, 1000, 1215752191]:
        event_status.new_event(new_event({"text": str(count), "count": count}))

    texts = query_texts_of_events(status_server, f"Filter: event_count = {value}")

    assert texts == {str(expected_count)}


@pytest.mark.parametrize(
    "value, expected_text",
    [
        pytest.param("0", "not in downtime", id="false"),
        pytest.param("1", "in downtime", id="true"),
    ],
)
def test_bool_filter_value_is_parsed_like_an_int_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, value: str, expected_text: str
) -> None:
    event_status.new_event(new_event({"text": "not in downtime", "host_in_downtime": False}))
    event_status.new_event(new_event({"text": "in downtime", "host_in_downtime": True}))

    texts = query_texts_of_events(status_server, f"Filter: event_host_in_downtime = {value}")

    assert texts == {expected_text}


@pytest.mark.parametrize(
    "value, expected_texts",
    [
        pytest.param("1.5", {"1", "2", "1e9"}, id="fraction"),
        pytest.param("2e9", {"2", "1e9"}, id="exponent"),
    ],
)
def test_time_filter_value_is_parsed_like_atoi_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, value: str, expected_texts: set[str]
) -> None:
    for text, first in [("1", 1.0), ("2", 2.0), ("1e9", 1e9)]:
        event_status.new_event(new_event({"text": text, "first": first}))

    texts = query_texts_of_events(status_server, f"Filter: event_first >= {value}")

    assert texts == expected_texts


# Without any messages, the rate is 0.0, so these filters would select the status the other
# way round if their value became 0.
@pytest.mark.parametrize(
    "filter_line, selected",
    [
        pytest.param("Filter: status_message_rate >= 1e3x",   False, id="trailing garbage"),
        pytest.param("Filter: status_message_rate > -0x1p-2", True,  id="hexadecimal"),
        pytest.param("Filter: status_message_rate > -inf",    True,  id="infinity"),
        pytest.param("Filter: status_message_rate > abc",     False, id="no number"),
    ],
)  # fmt: skip
def test_double_filter_value_is_parsed_like_atof_in_livestatus(
    status_server: StatusServer, filter_line: str, selected: bool
) -> None:
    status_socket = query_status_server(
        status_server, f"GET status\nColumns: status_message_rate\n{filter_line}"
    )

    _header, *rows = status_socket.get_response()
    assert bool(rows) is selected


@pytest.mark.parametrize(
    "header_line",
    [
        pytest.param("Or: 2", id="Or"),
        pytest.param("Negate:", id="Negate"),
        pytest.param("Stats: event_state = 0", id="Stats"),
        pytest.param("AuthUser: alice", id="AuthUser"),
        # Unlike Livestatus, even if the EC behaves like that anyway
        pytest.param("ColumnHeaders: on", id="ColumnHeaders"),
        pytest.param("KeepAlive: on", id="KeepAlive"),
        pytest.param("Filter :event_id = 1", id="space in front of the colon"),
    ],
)
def test_header_not_implemented_by_the_event_console_is_rejected(
    status_server: StatusServer, header_line: str
) -> None:
    with pytest.raises(MKClientError, match="Invalid header line"):
        query_status_server(status_server, f"GET events\n{header_line}")


@pytest.mark.parametrize("operator_name, argument, expected_texts", LIST_FILTER_CASES)
def test_list_column_filter_works_like_in_livestatus(
    event_status: EventStatus,
    status_server: StatusServer,
    operator_name: str,
    argument: str,
    expected_texts: set[str],
) -> None:
    for event in EVENTS_WITH_CONTACT_GROUPS:
        event_status.new_event(new_event(event))

    texts = query_texts_of_events(
        status_server, f"Filter: event_contact_groups {operator_name} {argument}"
    )

    assert texts == expected_texts


def test_in_operator_is_rejected_for_list_columns(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Invalid header line"):
        query_status_server(status_server, "GET events\nFilter: event_contact_groups in admins")


@pytest.mark.parametrize(
    "filter_line",
    [
        pytest.param("Filter: event_count < 0",          id="large value wraps to a negative one"),
        pytest.param("Filter: event_count = 3000000000", id="both values wrap"),
    ],
)  # fmt: skip
def test_int_row_value_is_compared_as_32_bits_like_in_livestatus(
    event_status: EventStatus, status_server: StatusServer, filter_line: str
) -> None:
    event_status.new_event(new_event({"text": "small", "count": 5}))
    event_status.new_event(new_event({"text": "large", "count": 3_000_000_000}))

    texts = query_texts_of_events(status_server, filter_line)

    assert texts == {"large"}


@pytest.mark.parametrize("operator_name, argument, expected_texts", TIME_FILTER_CASES)
def test_time_filter_compares_the_truncated_time_like_livestatus(
    event_status: EventStatus,
    status_server: StatusServer,
    operator_name: str,
    argument: str,
    expected_texts: set[str],
) -> None:
    for event in EVENTS_WITH_FIRST_TIMES:
        event_status.new_event(new_event(event))

    texts = query_texts_of_events(status_server, f"Filter: event_first {operator_name} {argument}")

    assert texts == expected_texts


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("GET events\nFilter: event_state ~ 2",              id="regex on an int column"),
        pytest.param("GET events\nFilter: event_host_in_downtime !~~ 1", id="regex on a bool column"),
        pytest.param("GET events\nFilter: event_first =~ 1",             id="equal ignoring case on a time column"),
        pytest.param("GET status\nFilter: status_message_rate ~ 1",      id="regex on a double column"),
        pytest.param("GET events\nFilter: event_state in 1 2",           id="in on an int column"),
    ],
)  # fmt: skip
def test_string_operator_is_rejected_for_other_columns(
    status_server: StatusServer, query: str
) -> None:
    with pytest.raises(MKClientError, match="Invalid header line"):
        query_status_server(status_server, query)


@pytest.mark.parametrize(
    "operator_name",
    [
        pytest.param("~", id="regex matches"),
        pytest.param("!~", id="regex does not match"),
        pytest.param("~~", id="regex matches ignoring case"),
        pytest.param("!~~", id="regex does not match ignoring case"),
    ],
)
def test_invalid_regex_fails_before_replying(
    event_status: EventStatus, status_server: StatusServer, operator_name: str
) -> None:
    event_status.new_event(new_event({"text": "disk full", "core_host": None}))
    status_socket = FakeStatusSocket(
        f"GET events\nOutputFormat: plain\nFilter: event_text {operator_name} \\p{{Lu}}\n".encode()
    )

    with pytest.raises(MKClientError, match="Invalid header line"):
        status_server.handle_client(status_socket, True, "127.0.0.1")

    assert status_socket.get_raw_response() == b""


def test_rules_table_shows_the_rule_hits(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)

    status_socket = query_status_server(status_server, "GET rules")

    assert status_socket.get_response() == [["rule_id", "rule_hits"], ["disk", 1]]


def test_status_table_shows_the_number_of_open_events(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "disk full"}))

    status_socket = query_status_server(
        status_server, "GET status\nColumns: status_num_open_events"
    )

    assert status_socket.get_response() == [["status_num_open_events"], [1]]


def test_history_table_shows_what_happened_to_the_events(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event({"text": "disk full"}))

    status_socket = query_status_server(
        status_server, "GET history\nColumns: history_what event_text"
    )

    assert status_socket.get_response() == [["history_what", "event_text"], ["NEW", "disk full"]]


def test_unknown_table_is_refused(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Invalid table: hosts"):
        query_status_server(status_server, "GET hosts")


@pytest.mark.parametrize(
    "output_format, expected_response",
    [
        pytest.param("plain", b"event_text\tevent_count\ndisk full\t1\n", id="plain"),
        pytest.param("json", b'[["event_text", "event_count"], ["disk full", 1]]\n', id="JSON"),
        pytest.param("python", b"[['event_text', 'event_count'], ['disk full', 1]]\n", id="Python"),
    ],
)
def test_events_are_shown_in_the_requested_output_format(
    event_status: EventStatus,
    status_server: StatusServer,
    output_format: str,
    expected_response: bytes,
) -> None:
    event_status.new_event(new_event({"text": "disk full"}))

    status_socket = query_status_server(
        status_server,
        f"GET events\nColumns: event_text event_count\nOutputFormat: {output_format}",
    )

    assert status_socket.get_raw_response() == expected_response


def test_several_queries_on_one_connection_are_answered_in_order(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)

    status_socket = query_status_server(
        status_server, "GET rules\nColumns: rule_id\n\nGET rules\nColumns: rule_hits"
    )

    assert status_socket.get_raw_response() == b"[['rule_id'], ['disk']]\n[['rule_hits'], [1]]\n"
