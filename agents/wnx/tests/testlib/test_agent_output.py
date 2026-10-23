#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import threading
import time
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager

import pytest
from testlib.agent_output import read_agent_output


def _serve(listener: socket.socket, payload: bytes) -> None:
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        with conn:
            conn.sendall(payload)


@contextmanager
def _fake_agent(serve: Callable[[socket.socket], None]) -> Generator[int]:
    listener = socket.create_server(("127.0.0.1", 0))
    thread = threading.Thread(target=serve, args=(listener,), daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        # close() alone does not wake a thread blocked in accept() on Linux.
        listener.shutdown(socket.SHUT_RDWR)
        listener.close()
        thread.join(5)
    assert not thread.is_alive(), "the fake agent did not stop"


@pytest.fixture(name="agent_port")
def _agent_port(request: pytest.FixtureRequest) -> Iterator[int]:
    with _fake_agent(lambda listener: _serve(listener, request.param)) as port:
        yield port


@pytest.mark.parametrize("agent_port", [b"<<<check_mk>>>\r\nVersion: 2.6\r\n"], indirect=True)
def test_returns_what_the_agent_sends(agent_port: int) -> None:
    output = read_agent_output("127.0.0.1", agent_port, tries=1, delay=0)

    assert output.splitlines() == ["<<<check_mk>>>", "Version: 2.6"]


def test_utf8_split_across_two_sends_comes_back_intact() -> None:
    first, second = "Straße Ö".encode()[:-1], "Straße Ö".encode()[-1:]

    def serve_split(listener: socket.socket) -> None:
        # The two bytes of "Ö" arrive in two separate reads.
        conn, _ = listener.accept()
        with conn:
            conn.sendall(first)
            time.sleep(0.1)
            conn.sendall(second)

    with _fake_agent(serve_split) as port:
        output = read_agent_output("127.0.0.1", port, tries=1, delay=0)

    assert output == "Straße Ö"


@pytest.mark.parametrize("agent_port", [b""], indirect=True)
def test_empty_output_fails_naming_endpoint_and_tries(agent_port: int) -> None:
    with pytest.raises(AssertionError, match=rf"127\.0\.0\.1:{agent_port} after 2 tries"):
        read_agent_output("127.0.0.1", agent_port, tries=2, delay=0)


@pytest.mark.parametrize("agent_port", [b""], indirect=True)
def test_empty_output_is_returned_when_allowed(agent_port: int) -> None:
    output = read_agent_output("127.0.0.1", agent_port, tries=2, delay=0, empty_ok=True)

    assert output == ""


def test_an_agent_that_answers_on_a_later_try_is_read() -> None:
    def serve_second(listener: socket.socket) -> None:
        # Like an agent still starting: the first connection gets nothing.
        conn, _ = listener.accept()
        conn.close()
        conn, _ = listener.accept()
        with conn:
            conn.sendall(b"<<<check_mk>>>\r\n")

    with _fake_agent(serve_second) as port:
        output = read_agent_output("127.0.0.1", port, tries=3, delay=0)

    assert output.splitlines() == ["<<<check_mk>>>"]


@pytest.mark.parametrize("empty_ok", [False, True])
def test_refused_connections_are_retried_then_fail(empty_ok: bool) -> None:
    with socket.create_server(("127.0.0.1", 0)) as s:
        port = s.getsockname()[1]  # closed again: nothing listens there

    with pytest.raises(
        AssertionError, match=rf"127\.0\.0\.1:{port} after 3 tries, the last one failed: Connection"
    ):
        read_agent_output("127.0.0.1", port, tries=3, delay=0, timeout=1, empty_ok=empty_ok)


def _accept_and_stay_silent(listener: socket.socket) -> None:
    held = []
    while True:
        try:
            held.append(listener.accept()[0])
        except OSError:
            break
    for conn in held:
        conn.close()


def _trickle(listener: socket.socket) -> None:
    # Never done: one byte every 50 ms, each well within a single recv timeout.
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        with conn:
            try:
                while True:
                    conn.sendall(b"x")
                    time.sleep(0.05)
            except OSError:
                pass


@pytest.mark.parametrize("serve", [_accept_and_stay_silent, _trickle], ids=["silent", "too_slow"])
def test_an_agent_that_does_not_finish_in_time_fails_after_one_try(
    serve: Callable[[socket.socket], None],
) -> None:
    with (
        _fake_agent(serve) as port,
        pytest.raises(AssertionError, match=r"after 1 try, the last one failed: TimeoutError"),
    ):
        read_agent_output("127.0.0.1", port, tries=3, delay=0, timeout=0.3)
