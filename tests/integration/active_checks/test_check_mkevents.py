#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs check_mkevents against a fake status socket with the events table of the Event Console"""

import errno
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


class _IPv6StatusServer(socketserver.TCPServer):
    address_family: int = socket.AF_INET6

    def __init__(self, events: Sequence[Event]) -> None:
        super().__init__(("::1", 0), _StatusRequestHandler)
        self.table = _events_table(events)


# Only the events table is the real one: The loop over the queries, the plain output and closing
# the connection without an answer on a client error are copies of StatusServer.handle_client()
# and _answer_query(), so a change there doesn't show up in these tests. A real StatusServer would
# need the settings, the config, the history and the event server the unit tests of cmk-ec build.
class _StatusRequestHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        assert isinstance(self.server, _StatusServer | _IPv6StatusServer)
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
            time.sleep(_SHORT_TIMEOUT + 0.5)  # more than the timeout of the check
            self.request.sendall(b"event_phase\tevent_state\tevent_text\n")
            self.request.shutdown(socket.SHUT_WR)
        finally:
            os.kill(pid, signal.SIGCONT)


class _NoEventsHandler(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        while self.request.recv(4096):
            pass
        self.request.sendall(b"event_phase\tevent_state\tevent_text\n")


@contextmanager
def _serving(server: socketserver.BaseServer) -> Iterator[None]:
    with server:
        # shutdown() waits for the next poll, by default up to half a second.
        threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        ).start()
        try:
            yield
        finally:
            server.shutdown()


def _accept_queue_length(listener: socket.socket) -> int:
    # For a listener, tcpi_unacked of struct tcp_info is its accept queue length.
    info = listener.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 32)
    length: int = struct.unpack_from("I", info, 24)[0]
    return length


@contextmanager
def _unresponsive_listener(address: str) -> Iterator[socket.socket]:
    """A listener with a full accept queue, so the kernel drops connection attempts"""
    with (
        socket.create_server((address, 0), backlog=0) as listener,
        socket.socket(listener.family) as filler,
    ):
        filler.connect(listener.getsockname())
        # Under load, the kernel may queue the filler only after connect() has returned.
        while _accept_queue_length(listener) == 0:
            time.sleep(0.001)
        yield listener


@contextmanager
def _unresponsive_unix_listener(socket_path: Path) -> Iterator[None]:
    """A UNIX listener with a full accept queue, so connecting waits, even when late"""
    with socket.socket(socket.AF_UNIX) as listener, socket.socket(socket.AF_UNIX) as filler:
        listener.bind(str(socket_path))
        listener.listen(0)
        filler.connect(str(socket_path))
        yield


@pytest.fixture(name="socket_path")
def fixture_socket_path() -> Iterator[Path]:
    # The temporary directories of Bazel are too deep for the path of a UNIX socket.
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        yield Path(directory) / "status"


@pytest.fixture(name="ipv6_loopback")
def fixture_ipv6_loopback() -> None:
    try:
        with socket.socket(socket.AF_INET6) as sock:
            sock.bind(("::1", 0))
    except OSError as e:
        if e.errno not in {errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT}:
            raise
        pytest.skip(f"No IPv6 on the loopback interface, e.g. in some Docker containers: {e}")


@pytest.fixture(name="ipv6_sockets")
def fixture_ipv6_sockets() -> None:
    """IPv6 sockets, maybe without addresses, enough to fail connecting to multicast"""
    try:
        socket.socket(socket.AF_INET6).close()
    except OSError as e:
        if e.errno != errno.EAFNOSUPPORT:
            raise
        pytest.skip(f"No IPv6 in the kernel: {e}")


# The timeout for tests waiting for the check to time out, with slack for a loaded machine
_SHORT_TIMEOUT = 2


def _run_check(
    *args: str, env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.environ["CHECK_MKEVENTS"], *args],
        capture_output=True,
        encoding="utf-8",
        timeout=30,
        check=False,
        env=None if env is None else {**os.environ, **env},
    )


# A name fake_network.c resolves to the addresses in FAKE_NETWORK_ADDRESSES
_FAKE_NAME = "eventconsole.test"


def _fake_network_env(*addresses: str, **variables: str) -> Mapping[str, str]:
    """The environment for fake_network.c, resolving _FAKE_NAME to the addresses"""
    return {
        "LD_PRELOAD": str(Path(os.environ["FAKE_NETWORK"]).absolute()),
        "FAKE_NETWORK_ADDRESSES": ",".join(addresses),
        **variables,
    }


def _polls_between_connects(log: Path) -> Sequence[Sequence[int]]:
    """The check's poll() timeouts in ms between its connects, which load can only lower"""
    polls: list[list[int]] = [[]]
    for call, value in struct.iter_unpack("=ii", log.read_bytes()):
        if call == 1:  # connect()
            polls.append([])
        else:  # poll()
            polls[-1].append(value)
    return polls


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
    with _unresponsive_listener("127.0.0.1") as server:
        port = server.getsockname()[1]

        result = _run_check("-t", str(_SHORT_TIMEOUT), "-H", f"127.0.0.1:{port}", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        (
            f"UNKNOWN - Cannot connect to event console at 127.0.0.1:{port}"
            f" (timeout after {_SHORT_TIMEOUT} seconds)\n"
        ),
    )


def test_connecting_via_unix_socket_to_an_unresponsive_event_console_times_out(
    socket_path: Path,
) -> None:
    with _unresponsive_unix_listener(socket_path):
        result = _run_check("-t", "1", "-s", str(socket_path), "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        (
            f"UNKNOWN - Cannot connect to event daemon via UNIX socket {socket_path}"
            " (timeout after 1 second)\n"
        ),
    )


def test_slowly_answering_event_console_times_out(socket_path: Path) -> None:
    with _serving(socketserver.UnixStreamServer(str(socket_path), _TrickleHandler)):
        # A byte per second, so only a timeout for the whole answer expires.
        result = _run_check("-t", str(_SHORT_TIMEOUT), "-s", str(socket_path), "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        f"UNKNOWN - Error while reading response (timeout after {_SHORT_TIMEOUT} seconds)\n",
    )


def test_reading_stops_at_the_deadline_although_data_is_waiting(socket_path: Path) -> None:
    with _serving(socketserver.UnixStreamServer(str(socket_path), _AnswerAfterTheDeadlineHandler)):
        result = _run_check("-t", str(_SHORT_TIMEOUT), "-s", str(socket_path), "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        f"UNKNOWN - Error while reading response (timeout after {_SHORT_TIMEOUT} seconds)\n",
    )


def test_ipv4_address_is_used_if_no_ipv6_network_is_reachable() -> None:
    server = socketserver.TCPServer(("127.0.0.1", 0), _NoEventsHandler)
    with _serving(server):
        result = _run_check(
            "-H",
            _FAKE_NAME,
            "myhost",
            # unreachable via TCP, like IPv6 from a host with IPv4 only
            env=_fake_network_env("ff02::1", f"127.0.0.1#{server.server_address[1]}"),
        )

    assert (result.returncode, result.stdout) == (0, "OK - no events for myhost\n")


def test_hanging_ipv6_lookup_doesnt_hold_up_the_ipv4_address() -> None:
    server = socketserver.TCPServer(("127.0.0.1", 0), _NoEventsHandler)
    with _serving(server):
        # The default timeout, as the check must answer before it, even under load. How briefly
        # IPv4 waits for IPv6 is up to the gtests of ConnectionSchedule.
        result = _run_check(
            "-H",
            _FAKE_NAME,
            "myhost",
            env=_fake_network_env(
                "ff02::1",
                f"127.0.0.1#{server.server_address[1]}",
                # like an unanswered AAAA query, longer than _run_check() waits
                FAKE_NETWORK_IPV6_DELAY="60",
            ),
        )

    assert (result.returncode, result.stdout) == (0, "OK - no events for myhost\n")


def test_slow_address_can_still_win_against_the_next_one(tmp_path: Path) -> None:
    log = tmp_path / "calls.log"
    slow_server = socketserver.TCPServer(("127.0.0.1", 0), _NoEventsHandler)
    with _unresponsive_listener("127.0.0.2") as unresponsive_server, _serving(slow_server):
        result = _run_check(
            "-H",
            _FAKE_NAME,
            "myhost",
            env=_fake_network_env(
                f"127.0.0.1#{slow_server.server_address[1]}",
                f"127.0.0.2#{unresponsive_server.getsockname()[1]}",
                # The first attempt seems to go on until the second one starts.
                FAKE_NETWORK_SLOW_CONNECT="1",
                FAKE_NETWORK_LOG=str(log),
            ),
        )

    assert (result.returncode, result.stdout) == (0, "OK - no events for myhost\n")
    # The first attempt won after the second one had started.
    assert len(_polls_between_connects(log)) == 3


def test_slow_name_resolution_counts_against_the_timeout(tmp_path: Path) -> None:
    log = tmp_path / "calls.log"
    with _unresponsive_listener("127.0.0.1") as server:
        port = server.getsockname()[1]

        result = _run_check(
            "-t",
            "4",
            "-H",
            f"127.0.0.1:{port}",
            "myhost",
            # Resolving leaves 2 seconds of slack, like _SHORT_TIMEOUT.
            env=_fake_network_env(FAKE_NETWORK_DELAY="2", FAKE_NETWORK_LOG=str(log)),
        )

    assert (result.returncode, result.stdout) == (
        3,
        (
            f"UNKNOWN - Cannot connect to event console at 127.0.0.1:{port}"
            " (timeout after 4 seconds)\n"
        ),
    )
    # Connecting waits for the 2 seconds left at most, not another 4.
    assert all(timeout <= 2000 for timeout in _polls_between_connects(log)[1])


def test_name_resolution_using_up_the_timeout_is_reported_as_such() -> None:
    # Only resolving can time out, so a short timeout is safe under load.
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]

        result = _run_check(
            "-t",
            "1",
            "-H",
            f"127.0.0.1:{port}",
            "myhost",
            # longer than _run_check() waits
            env=_fake_network_env(FAKE_NETWORK_DELAY="60"),
        )

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Cannot resolve the addresses of 127.0.0.1 (timeout after 1 second)\n",
    )


def test_unknown_zone_is_reported_as_unresolvable() -> None:
    # Unlike the gtests of ConnectionSchedule, this takes the answers of the real resolver for both
    # families. The zone is longer than any interface name.
    result = _run_check("-H", "[fe80::1%no-such-interface]:6558", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        (
            "UNKNOWN - Cannot resolve the addresses of fe80::1%no-such-interface"
            " (Name or service not known)\n"
        ),
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


@pytest.mark.usefixtures("ipv6_loopback")
def test_event_console_is_reachable_via_ipv6() -> None:
    events = [{"host": "myhost", "phase": "open", "state": 1, "text": ""}]
    server = _IPv6StatusServer(events)
    with _serving(server):
        result = _run_check("-H", f"[::1]:{server.server_address[1]}", "myhost")

    assert (result.returncode, result.stdout) == (1, "WARN - 1 events (1 unacknowledged)\n")


@pytest.mark.usefixtures("ipv6_loopback")
def test_refused_ipv6_connection_shows_the_address_in_brackets() -> None:
    with socket.socket(socket.AF_INET6) as unused:
        unused.bind(("::1", 0))  # Reserves a port without listening on it.
        port = unused.getsockname()[1]

        result = _run_check("-H", f"[::1]:{port}", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        f"UNKNOWN - Cannot connect to event console at [::1]:{port} (Connection refused)\n",
    )


@pytest.mark.usefixtures("ipv6_sockets")
def test_zone_of_an_ipv6_address_is_kept() -> None:
    result = _run_check("-H", "ff02::1%lo", "myhost")  # TCP can't connect to a multicast address.

    assert (result.returncode, result.stdout) == (
        3,
        (
            "UNKNOWN - Cannot connect to event console at [ff02::1%lo]:6558"
            " (Network is unreachable)\n"
        ),
    )


def test_invalid_remote_address_is_reported() -> None:
    result = _run_check("-H", "localhost:0", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        (
            "UNKNOWN - Invalid remote address 'localhost:0', expected HOST[:PORT],"
            " e.g. myhost:6558 or [2001:db8::1]:6558\n"
        ),
    )


def test_default_port_is_6558() -> None:
    result = _run_check("-H", "224.0.0.1", "myhost")  # TCP can't connect to a multicast address.

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Cannot connect to event console at 224.0.0.1:6558 (Network is unreachable)\n",
    )


def test_port_option_applies_to_a_remote_address_without_a_port() -> None:
    # TCP can't connect to a multicast address.
    result = _run_check("-p", "6559", "-H", "224.0.0.1", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Cannot connect to event console at 224.0.0.1:6559 (Network is unreachable)\n",
    )


def test_invalid_port_option_is_reported() -> None:
    result = _run_check("-p", "0", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Invalid port '0', expected 1 to 65535\n",
    )


def test_invalid_timeout_is_reported() -> None:
    result = _run_check("-t", "0", "myhost")

    assert (result.returncode, result.stdout) == (
        3,
        "UNKNOWN - Invalid timeout '0', expected 1 to 3600 seconds\n",
    )


def _no_answer(peer: str | None = None) -> str:
    """The first line of the output for a connection closed without an answer"""
    at = "" if peer is None else f" at {peer}"
    return (
        f"UNKNOWN - Event console{at} closed the connection without answering, see its log file"
        " var/log/mkeventd.log for the reason, e.g. a denied access via TCP or an invalid regular"
        " expression for the application"
    )


def test_connection_closed_while_sending_the_query_is_reported(socket_path: Path) -> None:
    # With the default socket buffer of 208 KiB, the check is still sending the
    # query when the connection gets closed. With a larger buffer, it may notice
    # the closed connection only while reading the answer, with the same output.
    with _serving(socketserver.UnixStreamServer(str(socket_path), _HangUpHandler)):
        result = _run_check("-s", str(socket_path), "a" * 120_000, "b" * 120_000)

    assert (result.returncode, result.stdout.splitlines()[0]) == (3, _no_answer())


def test_denied_access_via_tcp_is_reported() -> None:
    server = socketserver.TCPServer(("127.0.0.1", 0), _HangUpHandler)
    port = server.server_address[1]
    with _serving(server):
        result = _run_check("-H", f"127.0.0.1:{port}", "myhost")

    assert (result.returncode, result.stdout.splitlines()[0]) == (
        3,
        _no_answer(f"127.0.0.1:{port}"),
    )


def test_invalid_application_regex_is_reported(socket_path: Path) -> None:
    result = _check_events(socket_path, [], "myhost", "my(app")

    assert (result.returncode, result.stdout.splitlines()[0]) == (3, _no_answer())


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
