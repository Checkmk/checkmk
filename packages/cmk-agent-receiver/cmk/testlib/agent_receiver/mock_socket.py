#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import dataclasses
import queue
import secrets
import select
import socket
import threading
import time
from collections.abc import Iterator


@dataclasses.dataclass
class ConnectionData:
    """Data received from a single socket connection."""

    socket_id: str
    data: bytes


@dataclasses.dataclass
class MockSocket:
    socket_path: str
    soc: socket.socket
    buffer_size: int
    socket_timeout: float
    delay: float | None = None
    data_queue: queue.SimpleQueue[ConnectionData] = dataclasses.field(init=False)

    # This threading barrier is used to synchronize the main (calling) thread with the socket thread
    # about the moment when the socket itself is ready to be used. Must be `wait`-ed in both
    # threads before that moment.
    _start_barrier: threading.Barrier = threading.Barrier(2, timeout=5)

    # This threading event is used to signal the socket thread that it must finish at an
    # appropriate moment.
    _stop_event: threading.Event = threading.Event()
    _running_thread: threading.Thread | None = None

    def __post_init__(self) -> None:
        self.data_queue = queue.SimpleQueue()

    def start(self) -> None:
        def thread_func() -> None:
            soc = self.soc
            _ = self._start_barrier.wait()
            while not self._stop_event.is_set():
                # Check if the socket is ready to be used
                rlist, _, _ = select.select([soc], [], [], 0.5)
                if rlist:
                    soc.settimeout(self.socket_timeout)
                    try:
                        conn, _ = soc.accept()
                        socket_id = str(secrets.token_urlsafe(6))
                        conn.settimeout(self.socket_timeout)
                        if self.delay:
                            time.sleep(self.delay)

                        # Collect all data from this connection
                        all_data = b""
                        data = conn.recv(self.buffer_size)
                        while data != b"":
                            all_data += data
                            data = conn.recv(self.buffer_size)

                        # Put the complete connection data
                        if all_data:
                            self.data_queue.put_nowait(
                                ConnectionData(socket_id=socket_id, data=all_data)
                            )

                        conn.shutdown(socket.SHUT_RDWR)
                        conn.close()
                    except TimeoutError:
                        pass
                else:
                    # If the socket is not ready yet, wait just a bit more.
                    time.sleep(0.1)

        self._start_barrier.reset()
        self._stop_event.clear()
        self._running_thread = threading.Thread(target=thread_func)
        self._running_thread.start()
        self._start_barrier.wait()

    def stop(self) -> None:
        self._stop_event.set()
        self._start_barrier.reset()
        if not self._running_thread:
            return
        self._running_thread.join()
        self._running_thread = None
        self._stop_event.clear()

    @property
    def is_running(self) -> bool:
        return self._running_thread is not None and self._running_thread.is_alive()

    @property
    def fileno(self) -> int:
        return self.soc.fileno()


@contextlib.contextmanager
def create_socket(
    *, socket_path: str, socket_timeout: float, buffer_size: int = 1024, delay: float | None = None
) -> Iterator[MockSocket]:
    with (
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as soc,
    ):
        soc.bind(socket_path)
        soc.listen()
        ms = MockSocket(
            soc=soc,
            socket_path=socket_path,
            buffer_size=buffer_size,
            socket_timeout=socket_timeout,
            delay=delay,
        )
        ms.start()
        yield ms
        ms.stop()


@contextlib.contextmanager
def create_non_listening_socket(socket_path: str) -> Iterator[str]:
    with (
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as soc,
    ):
        # bind, but don't listen (also works without it)
        soc.bind(socket_path)
        yield socket_path


@contextlib.contextmanager
def create_unresponsive_socket(socket_path: str) -> Iterator[str]:
    """
    Create a socket that accepts connections but never reads data.

    This simulates an unresponsive CMC server. When a client tries to send
    a large payload (exceeding the socket buffer), sendall() will block waiting
    for the server to read data. After socket_timeout seconds, sendall() will
    raise socket.timeout (OSError).
    """
    stop_event = threading.Event()
    start_barrier = threading.Barrier(2, timeout=5)

    def accept_but_dont_read() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as soc:
            soc.bind(socket_path)
            soc.listen()
            soc.settimeout(0.5)  # Allow stopping the thread
            start_barrier.wait()

            while not stop_event.is_set():
                try:
                    conn, _ = soc.accept()
                    # Accept the connection but never call recv()
                    # This causes the client's sendall() to block and eventually timeout
                    # Keep the connection open until stop_event is set
                    while not stop_event.is_set():
                        time.sleep(0.1)
                    conn.close()
                except TimeoutError:
                    continue  # Check stop_event again

    thread = threading.Thread(target=accept_but_dont_read)
    thread.start()
    start_barrier.wait()

    try:
        yield socket_path
    finally:
        stop_event.set()
        thread.join()


@contextlib.contextmanager
def create_crashy_socket(socket_path: str) -> Iterator[str]:
    """
    Create a socket that accepts connections and then immediately closes them.

    This simulates a CMC server that crashes or closes the connection unexpectedly
    during data transmission. When the client tries to send data, it will receive
    BrokenPipeError (EPIPE).
    """
    stop_event = threading.Event()
    start_barrier = threading.Barrier(2, timeout=5)

    def accept_and_close() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as soc:
            soc.bind(socket_path)
            soc.listen()
            soc.settimeout(0.5)
            start_barrier.wait()

            while not stop_event.is_set():
                try:
                    conn, _ = soc.accept()
                    try:
                        # Read one byte to ensure the client has started sending.
                        # This blocks until data arrives, guaranteeing we shutdown
                        # mid-transmission. Works reliably for payloads > socket buffer.
                        conn.settimeout(0.5)
                        _ = conn.recv(1)
                    except TimeoutError:
                        pass  # No data received, close anyway
                    # Shutdown the connection to signal termination to the peer
                    conn.shutdown(socket.SHUT_RDWR)
                    conn.close()
                except TimeoutError:
                    continue

    thread = threading.Thread(target=accept_and_close)
    thread.start()
    start_barrier.wait()

    try:
        yield socket_path
    finally:
        stop_event.set()
        thread.join()
