#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs check_mkevents against a fake status socket with the events table of the Event Console"""

import logging
import os
import socketserver
import subprocess
import tempfile
import threading
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import override

import pytest

from cmk.ec.history import quote_tab
from cmk.ec.main import Queries, StatusTableEvents
from cmk.ec.query import MKClientError, Query, QueryGET, request_lines

Event = Mapping[str, object]


def _events_table(events: Sequence[Event]) -> StatusTableEvents:
    return StatusTableEvents(logging.getLogger(__name__), lambda: events)


class _StatusServer(socketserver.UnixStreamServer):
    def __init__(self, socket_path: Path, events: Sequence[Event]) -> None:
        super().__init__(str(socket_path), _StatusRequestHandler)
        self.table = _events_table(events)


# Only the events table is the real one: The loop over the queries, the plain output and closing
# the connection without an answer on a client error are copies of StatusServer.handle_client()
# and _answer_query(), so a change there doesn't show up in these tests. A real StatusServer would
# need the settings, the config, the history and the event server the unit tests of cmk-ec build.
class _StatusRequestHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        assert isinstance(self.server, _StatusServer)
        table = self.server.table
        for request in Queries(self.request):
            try:
                query = Query.make(
                    lambda _name: table, request_lines(request), logging.getLogger(__name__)
                )
            except MKClientError:
                return  # Like the Event Console, close the connection without an answer.
            if isinstance(query, QueryGET):
                for row in table.query(query):
                    self.request.sendall(b"\t".join(quote_tab(column) for column in row) + b"\n")


class _NoLineBreaksHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        while self.request.recv(4096):
            pass
        # Like another service on the port, and the 1000th byte is within an "ä".
        self.request.sendall(("x" + "ä" * 1000).encode())


class _CutOffAnswerHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        while self.request.recv(4096):
            pass
        # Like an Event Console stopped in the middle of the row of a CRIT event
        self.request.sendall(b"event_phase\tevent_state\tevent_text\nopen\t0\tfine\nopen\t2")


@pytest.fixture(name="socket_path")
def fixture_socket_path() -> Iterator[Path]:
    # The temporary directories of Bazel are too deep for the path of a UNIX socket.
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        yield Path(directory) / "status"


def _run_check(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.environ["CHECK_MKEVENTS"], *args],
        capture_output=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def _check_events(
    socket_path: Path, events: Sequence[Event], *args: str
) -> subprocess.CompletedProcess[str]:
    with _StatusServer(socket_path, events) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            return _run_check("-s", str(socket_path), *args)
        finally:
            server.shutdown()


def test_event_with_empty_text_is_counted(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 2, "text": ""}]

    result = _check_events(socket_path, events, "myhost")

    assert (result.returncode, result.stdout) == (2, "CRIT - 1 events (1 unacknowledged)\n")


def test_event_text_with_newlines_belongs_to_one_event(socket_path: Path) -> None:
    events = [
        {"host": "myhost", "phase": "open", "state": 1, "text": "first line\nsecond line"},
        {"host": "myhost", "phase": "ack", "state": 0, "text": "\n"},
    ]

    result = _check_events(socket_path, events, "-L", "myhost")

    assert (result.returncode, result.stdout) == (
        1,
        "WARN - 2 events (1 unacknowledged)\nLast line: first line\nsecond line\n",
    )


def test_newlines_of_event_text_in_summary_become_spaces(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 1, "text": "first line\nsecond line"}]

    result = _check_events(socket_path, events, "-l", "myhost")

    assert (result.returncode, result.stdout) == (
        1,
        "WARN - 1 events (1 unacknowledged), Last line: first line second line\n",
    )


@pytest.mark.parametrize(
    "states", [pytest.param([3, 2], id="unknown first"), pytest.param([2, 3], id="crit first")]
)
def test_crit_is_worse_than_unknown(socket_path: Path, states: Sequence[int]) -> None:
    events = [
        {"host": "myhost", "phase": "open", "state": state, "text": f"state {state}"}
        for state in states
    ]

    result = _check_events(socket_path, events, "-l", "myhost")

    assert (result.returncode, result.stdout) == (
        2,
        "CRIT - 2 events (2 unacknowledged), Last line: state 2\n",
    )


@pytest.mark.parametrize("state", [4, "x"])
def test_invalid_event_state_is_reported(socket_path: Path, state: object) -> None:
    events = [{"host": "myhost", "phase": "open", "state": state, "text": ""}]

    result = _check_events(socket_path, events, "myhost")

    assert (result.returncode, result.stdout.splitlines()[0]) == (
        3,
        f"UNKNOWN - Event console answered with an invalid event state '{state}'",
    )


def test_only_the_start_of_a_long_invalid_event_state_is_shown(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": "x" * 1000, "text": ""}]

    result = _check_events(socket_path, events, "myhost")

    assert result.stdout.splitlines()[0] == (
        f"UNKNOWN - Event console answered with an invalid event state '{'x' * 20}[...]'"
    )


def test_only_the_start_of_a_long_invalid_answer_is_shown(socket_path: Path) -> None:
    events: list[Event] = [
        {"host": "myhost", "phase": "open", "state": 0, "text": f"event {i}"} for i in range(1000)
    ]
    events.append({"host": "myhost", "phase": "open", "state": 4, "text": ""})

    result = _check_events(socket_path, events, "myhost")

    assert result.returncode == 3
    shown = result.stdout.partition(" byte response:\n")[2]
    assert shown.endswith("\n[...]\n")  # cut at a line break
    assert len(shown.removesuffix("[...]\n")) <= 1000  # of about 17000 bytes


def test_long_invalid_answer_is_cut_between_characters(socket_path: Path) -> None:
    with socketserver.UnixStreamServer(str(socket_path), _NoLineBreaksHandler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            result = _run_check("-s", str(socket_path), "myhost")
        finally:
            server.shutdown()

    assert result.stdout.partition(" byte response:\n")[2] == "x" + "ä" * 499 + "[...]\n"


def test_line_break_near_the_start_doesnt_shorten_the_shown_answer(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 4, "text": "x" * 3000}]

    result = _check_events(socket_path, events, "myhost")

    start = "event_phase\tevent_state\tevent_text\nopen\t4\t"
    assert result.stdout.partition(" byte response:\n")[2] == (
        start + "x" * (1000 - len(start)) + "[...]\n"
    )


def test_answer_cut_off_within_a_line_is_reported(socket_path: Path) -> None:
    with socketserver.UnixStreamServer(str(socket_path), _CutOffAnswerHandler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            result = _run_check("-s", str(socket_path), "myhost")
        finally:
            server.shutdown()

    assert (result.returncode, result.stdout.splitlines()[0]) == (
        3,
        "UNKNOWN - Event console answered with an incomplete last line",
    )


def test_vertical_bar_is_replaced_like_in_checkmk(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 0, "text": "a|b"}]

    result = _check_events(socket_path, events, "-l", "myhost")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: a❘b\n"
