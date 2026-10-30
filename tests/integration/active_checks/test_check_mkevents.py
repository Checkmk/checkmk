#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs check_mkevents against a fake status socket with the events table of the Event Console"""

import logging
import os
import signal
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
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


class _HangUpHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        pass  # The server closes the connection without reading the query.


class _TrickleHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        while self.request.recv(4096):
            pass
        try:
            for byte in b"event_phase\tevent_state\tevent_text\n":
                self.request.sendall(bytes([byte]))
                time.sleep(1)
        except ConnectionError:
            pass  # The check gave up, as it should.


class _AnswerAfterTheDeadlineHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        pid, _uid, _gid = struct.unpack(
            "3i",
            self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")),
        )
        # The PID of a peer in another PID namespace is 0, and kill() would then stop
        # our whole process group, pytest included.
        assert pid > 0
        while self.request.recv(4096):
            pass
        # Stopped until after the deadline, the check then finds the whole answer
        # waiting, like with an Event Console sending faster than the check reads.
        os.kill(pid, signal.SIGSTOP)
        try:
            time.sleep(21)  # more than the timeout of the check
            self.request.sendall(b"event_phase\tevent_state\tevent_text\n")
            self.request.shutdown(socket.SHUT_WR)
        finally:
            os.kill(pid, signal.SIGCONT)


@contextmanager
def _serving(server: socketserver.BaseServer) -> Iterator[None]:
    with server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield
        finally:
            server.shutdown()


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
    with _serving(_StatusServer(socket_path, events)):
        return _run_check("-s", str(socket_path), *args)


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
    with _serving(socketserver.UnixStreamServer(str(socket_path), _NoLineBreaksHandler)):
        result = _run_check("-s", str(socket_path), "myhost")

    assert result.stdout.partition(" byte response:\n")[2] == "x" + "ä" * 499 + "[...]\n"


def test_line_break_near_the_start_doesnt_shorten_the_shown_answer(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 4, "text": "x" * 3000}]

    result = _check_events(socket_path, events, "myhost")

    start = "event_phase\tevent_state\tevent_text\nopen\t4\t"
    assert result.stdout.partition(" byte response:\n")[2] == (
        start + "x" * (1000 - len(start)) + "[...]\n"
    )


def test_answer_cut_off_within_a_line_is_reported(socket_path: Path) -> None:
    with _serving(socketserver.UnixStreamServer(str(socket_path), _CutOffAnswerHandler)):
        result = _run_check("-s", str(socket_path), "myhost")

    assert (result.returncode, result.stdout.splitlines()[0]) == (
        3,
        "UNKNOWN - Event console answered with an incomplete last line",
    )


def test_vertical_bar_is_replaced_like_in_checkmk(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 0, "text": "a|b"}]

    result = _check_events(socket_path, events, "-l", "myhost")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: a❘b\n"


def test_nul_byte_in_event_text_is_replaced_by_space(socket_path: Path) -> None:
    events = [{"host": "myhost", "phase": "open", "state": 1, "text": "a\0b"}]

    result = _check_events(socket_path, events, "-l", "myhost")

    assert result.stdout == "WARN - 1 events (1 unacknowledged), Last line: a b\n"


def _events_of_hosts(*hosts: str) -> Sequence[Event]:
    return [{"host": host, "phase": "open", "state": 0, "text": host} for host in hosts]


def test_host_list_matches_its_hosts(socket_path: Path) -> None:
    events = _events_of_hosts("myhost", "10.1.2.3", "otherhost")

    result = _check_events(socket_path, events, "myhost/10.1.2.3")

    assert result.stdout == "OK - 2 events (2 unacknowledged)\n"


def test_host_with_spaces_in_host_list_matches_only_itself(socket_path: Path) -> None:
    events = _events_of_hosts("DB server 1", "DB server 1\n", "db", "server", "1")

    result = _check_events(socket_path, events, "-l", "myhost/DB server 1")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: DB server 1\n"


def test_whitespace_around_a_single_host_is_ignored(socket_path: Path) -> None:
    events = _events_of_hosts("DB server", " DB server ")

    result = _check_events(socket_path, events, "-l", " DB server ")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: DB server\n"


def test_whitespace_around_a_host_in_a_host_list_is_ignored_like_for_a_single_one(
    socket_path: Path,
) -> None:
    events = _events_of_hosts("DB server", " DB server ")

    result = _check_events(socket_path, events, "-l", "myhost/ DB server ")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: DB server\n"


def test_quoted_slash_belongs_to_the_host(socket_path: Path) -> None:
    events = _events_of_hosts("Router A/B", "B")

    result = _check_events(socket_path, events, "-l", "-q", "myhost/Router A\\/B")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: Router A/B\n"


def test_no_events_shows_the_hosts_of_a_host_list_unquoted(socket_path: Path) -> None:
    result = _check_events(socket_path, [], "-q", "myhost/Router A\\/B")

    assert result.stdout == "OK - no events for myhost/Router A/B\n"


def test_backslash_is_part_of_the_host_without_quoting(socket_path: Path) -> None:
    events = _events_of_hosts("\\\\fs1", "\\fs1")

    result = _check_events(socket_path, events, "-l", "\\\\fs1")

    assert result.stdout == "OK - 1 events (1 unacknowledged), Last line: \\\\fs1\n"


def test_connecting_to_an_unresponsive_event_console_times_out() -> None:
    with socket.create_server(("127.0.0.1", 0), backlog=0) as server, socket.socket() as client:
        port = server.getsockname()[1]
        # Fill the accept queue, so the kernel drops further connection attempts.
        client.connect(("127.0.0.1", port))

        result = _run_check("-H", f"127.0.0.1:{port}", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        (
            f"UNKNOWN - Cannot connect to event console at 127.0.0.1:{port}"
            " (timeout after 20 seconds)\n"
        ),
    )


def test_slowly_answering_event_console_times_out(socket_path: Path) -> None:
    with _serving(socketserver.UnixStreamServer(str(socket_path), _TrickleHandler)):
        result = _run_check("-s", str(socket_path), "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Error while reading response (timeout after 20 seconds)\n",
    )


def test_reading_stops_at_the_deadline_although_data_is_waiting(socket_path: Path) -> None:
    with _serving(socketserver.UnixStreamServer(str(socket_path), _AnswerAfterTheDeadlineHandler)):
        result = _run_check("-s", str(socket_path), "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Error while reading response (timeout after 20 seconds)\n",
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["-a", "-s"], id="option without argument"),
        pytest.param(["-x", "myhost"], id="unknown option"),
        pytest.param(["-a"], id="no host"),
    ],
)
def test_malformed_command_line_shows_usage(args: Sequence[str]) -> None:
    result = _run_check(*args)

    assert result.returncode == 3
    assert result.stdout.startswith("UNKNOWN - Usage: check_mkevents ")


@pytest.mark.parametrize(
    "remote",
    [
        "",
        ":6558",
        "localhost:abc",
        "localhost:70000",
        "localhost:+80",
        "localhost: 80",
        "localhost:0",
    ],
)
def test_invalid_remote_address_is_reported(remote: str) -> None:
    result = _run_check("-H", remote, "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        f"UNKNOWN - Invalid remote address '{remote}', expected HOST[:PORT]\n",
    )


def test_empty_port_means_the_default_port() -> None:
    result = _run_check("-H", "224.0.0.1:", "myhost")  # TCP can't connect to a multicast address.

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Cannot connect to event console at 224.0.0.1:6558 (Network is unreachable)\n",
    )


def test_leading_zeros_of_the_port_dont_count() -> None:
    # TCP can't connect to a multicast address.
    result = _run_check("-H", "224.0.0.1:0006558", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Cannot connect to event console at 224.0.0.1:6558 (Network is unreachable)\n",
    )


_NO_ANSWER = (
    "UNKNOWN - Event console closed the connection without answering, see its log file"
    " var/log/mkeventd.log for the reason, e.g. a denied access via TCP or an invalid regular"
    " expression for the application"
)


def test_connection_closed_while_sending_the_query_is_reported(socket_path: Path) -> None:
    # With the default socket buffer of 208 KiB, the check is still sending the
    # query when the connection gets closed. With a larger buffer, it may notice
    # the closed connection only while reading the answer, with the same output.
    with _serving(socketserver.UnixStreamServer(str(socket_path), _HangUpHandler)):
        result = _run_check("-s", str(socket_path), "a" * 120_000, "b" * 120_000)

    assert (result.returncode, result.stdout.splitlines()[0]) == (3, _NO_ANSWER)


def test_denied_access_via_tcp_is_reported() -> None:
    server = socketserver.TCPServer(("127.0.0.1", 0), _HangUpHandler)
    with _serving(server):
        result = _run_check("-H", f"127.0.0.1:{server.server_address[1]}", "myhost")

    assert (result.returncode, result.stdout.splitlines()[0]) == (3, _NO_ANSWER)


def test_invalid_application_regex_is_reported(socket_path: Path) -> None:
    result = _check_events(socket_path, [], "myhost", "my(app")

    assert (result.returncode, result.stdout.splitlines()[0]) == (3, _NO_ANSWER)


def test_too_long_socket_path_is_reported(socket_path: Path) -> None:
    path = str(socket_path.parent / ("x" * 120))

    result = _run_check("-s", path, "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        (
            f"UNKNOWN - Cannot connect to event daemon via UNIX socket {path}"
            " (path longer than 107 bytes)\n"
        ),
    )


def test_application_may_start_with_a_dash(socket_path: Path) -> None:
    events = [{"host": "myhost", "application": "-app", "phase": "open", "state": 1, "text": ""}]

    result = _check_events(socket_path, events, "myhost", "-app")

    assert result.stdout == "WARN - 1 events (1 unacknowledged)\n"


def test_arguments_after_the_application_are_ignored(socket_path: Path) -> None:
    events = [{"host": "myhost", "application": "myapp", "phase": "ack", "state": 2, "text": ""}]

    result = _check_events(socket_path, events, "myhost", "myapp", "-a")

    assert result.stdout == "CRIT - 1 events (0 unacknowledged)\n"


def test_host_after_double_dash_may_start_with_a_dash(socket_path: Path) -> None:
    events = [{"host": "-host", "phase": "open", "state": 1, "text": ""}]

    result = _check_events(socket_path, events, "--", "-host")

    assert result.stdout == "WARN - 1 events (1 unacknowledged)\n"
