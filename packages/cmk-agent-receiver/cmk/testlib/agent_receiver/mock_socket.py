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
class DataChunk:
    socket_id: str
    data: bytes


@dataclasses.dataclass
class MockSocket:
    socket_path: str
    _soc: socket.socket
    _buffer_size: int
    _socket_timeout: float
    delay: float | None = None
    data_queue: queue.SimpleQueue[DataChunk] = dataclasses.field(init=False)

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
            soc = self._soc
            self._start_barrier.wait()
            while not self._stop_event.is_set():
                # Check if the socket is ready to be used
                rlist, _, _ = select.select([soc], [], [], 5.0)
                if rlist:
                    soc.settimeout(self._socket_timeout)
                    try:
                        conn, _ = soc.accept()
                        socket_id = str(secrets.token_urlsafe(6))
                        conn.settimeout(self._socket_timeout)
                        if self.delay:
                            time.sleep(self.delay)
                        data = conn.recv(self._buffer_size)
                        while data != b"":
                            self.data_queue.put_nowait(DataChunk(socket_id=socket_id, data=data))
                            data = conn.recv(self._buffer_size)
                        conn.shutdown(socket.SHUT_RDWR)
                        conn.close()
                    except TimeoutError:
                        pass
                else:
                    # If the socket is not ready yet, wait just a bit more.
                    time.sleep(0.2)

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
        return self._soc.fileno()


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
            _soc=soc,
            socket_path=socket_path,
            _buffer_size=buffer_size,
            _socket_timeout=socket_timeout,
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
