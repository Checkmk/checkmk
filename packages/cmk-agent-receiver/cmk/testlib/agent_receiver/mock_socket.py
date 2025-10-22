#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import dataclasses
import queue
import select
import socket
import tempfile
import threading
import time
from collections.abc import Iterator


@dataclasses.dataclass
class MockSocket:
    socket_path: str
    _soc: socket.socket
    _buffer_size: int
    data_queue: queue.SimpleQueue[bytes] = queue.SimpleQueue()

    # This threading barrier is used to synchronize the main (calling) thread with the socket thread
    # about the moment when the socket itself is ready to be used. Must be `wait`-ed in both
    # threads before that moment.
    _start_barrier: threading.Barrier = threading.Barrier(2, timeout=5)

    # This threading event is used to signal the socket thread that it must finish at an
    # appropriate moment.
    _stop_event: threading.Event = threading.Event()
    _running_thread: threading.Thread | None = None

    def start(self) -> None:
        def thread_func() -> None:
            soc = self._soc
            self._start_barrier.wait()
            while not self._stop_event.is_set():
                # Check if the socket is ready to be used
                rlist, _, _ = select.select([soc], [], [], 5.0)
                if rlist:
                    conn, _ = soc.accept()
                    data = conn.recv(self._buffer_size)
                    self.data_queue.put_nowait(data)
                    conn.close()
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


@contextlib.contextmanager
def create_socket(buffer_size: int = 1024) -> Iterator[MockSocket]:
    with (
        tempfile.TemporaryDirectory() as folder,
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as soc,
    ):
        socket_path = f"{folder}/test.sock"
        soc.bind(socket_path)
        soc.listen()
        ms = MockSocket(_soc=soc, socket_path=socket_path, _buffer_size=buffer_size)
        ms.start()
        yield ms
        ms.stop()
