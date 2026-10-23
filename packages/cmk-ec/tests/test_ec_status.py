#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.main import EventStatus, StatusServer
from cmk.ec.query import MKClientError

from .helpers import FakeStatusSocket, new_event


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
