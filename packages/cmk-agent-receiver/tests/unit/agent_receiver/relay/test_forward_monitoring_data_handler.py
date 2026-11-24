#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import logging
import queue
import re
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from cmk.agent_receiver.relay.api.routers.relays.handlers import ForwardMonitoringDataHandler
from cmk.agent_receiver.relay.api.routers.relays.handlers.forward_monitoring_data import (
    ForwardRefusedError,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
from cmk.relay_protocols.monitoring_data import PayloadType
from cmk.testlib.agent_receiver.mock_socket import create_busy_socket


@pytest.mark.asyncio
async def test_a_forward_is_refused_while_the_queue_stays_full(tmp_path: Path) -> None:
    # Not running, so nothing takes from the queue.
    handler = ForwardMonitoringDataHandler(
        data_socket=tmp_path / "raw-data", socket_timeout=1.0, queue_size=1, queue_wait=0.1
    )

    await _forward(handler, b"queued")
    with pytest.raises(ForwardRefusedError):
        await _forward(handler, b"refused")


@pytest.mark.asyncio
async def test_a_refusal_for_a_full_queue_is_logged_as_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    handler = ForwardMonitoringDataHandler(
        data_socket=tmp_path / "raw-data", socket_timeout=1.0, queue_size=1, queue_wait=0.1
    )

    await _forward(handler, b"queued")
    with caplog.at_level(logging.ERROR), pytest.raises(ForwardRefusedError):
        await _forward(handler, b"refused")

    assert "Refused monitoring data of host from relay relay" in caplog.text


@pytest.mark.asyncio
async def test_forwards_queued_at_shutdown_are_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    handler = ForwardMonitoringDataHandler(
        data_socket=tmp_path / "raw-data", socket_timeout=5.0, queue_size=8, queue_wait=1.0
    )

    with caplog.at_level(logging.ERROR), _core_stuck_on_large_payloads(tmp_path / "raw-data"):
        async with handler.running():
            # Large enough that every sender waits on the stuck core, so these stay queued.
            for _ in range(4):
                await _forward(handler, b"x" * 1024 * 1024)
            await _forward(handler, b"queued")
            await asyncio.sleep(0.2)

    assert "Dropped 1 queued forwards" in caplog.text


@pytest.mark.asyncio
async def test_a_failed_hand_over_is_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The relay already has its answer, so the log is the only place a failure shows."""
    handler = ForwardMonitoringDataHandler(data_socket=tmp_path / "missing", socket_timeout=1.0)

    with caplog.at_level(logging.ERROR):
        async with handler.running():
            await _forward(handler, b"payload")
            async with asyncio.timeout(2.0):
                while not caplog.records:
                    await asyncio.sleep(0.01)

    assert "Failed to forward monitoring data of host from relay relay" in caplog.text


@pytest.mark.asyncio
async def test_the_sender_survives_an_unexpected_error(tmp_path: Path) -> None:
    # A negative timeout makes the socket raise ValueError, which is no OSError.
    handler = ForwardMonitoringDataHandler(
        data_socket=tmp_path / "raw-data", socket_timeout=-1, queue_size=1, queue_wait=1.0
    )

    async with handler.running():
        # A dead sender stops taking items, so the third forward finds the queue full.
        for _ in range(3):
            await _forward(handler, b"payload")


_CHUNK = 65536


@contextmanager
def _core_stuck_on_large_payloads(path: Path) -> Iterator[queue.Queue[bytes]]:
    """Leave a connection unread if its header announces more than a chunk, read the rest."""
    received: queue.Queue[bytes] = queue.Queue()
    stop = threading.Event()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen(8)
        server.settimeout(0.05)
        stuck: list[socket.socket] = []

        def serve() -> None:
            while not stop.is_set():
                try:
                    conn, _ = server.accept()
                except TimeoutError:
                    continue
                conn.settimeout(None)
                first = conn.recv(_CHUNK)
                announced = re.search(rb"payload_size:(\d+);", first)
                if announced is not None and int(announced[1]) > _CHUNK:
                    stuck.append(conn)
                    continue
                with conn:
                    received.put(first + _read_to_end(conn))

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            yield received
        finally:
            stop.set()
            thread.join()
            for conn in stuck:
                conn.close()


def _read_to_end(conn: socket.socket) -> bytes:
    chunks = []
    while chunk := conn.recv(_CHUNK):
        chunks.append(chunk)
    return b"".join(chunks)


@pytest.mark.asyncio
async def test_a_slow_hand_over_does_not_hold_up_the_next(tmp_path: Path) -> None:
    handler = ForwardMonitoringDataHandler(
        data_socket=tmp_path / "raw-data", socket_timeout=5.0, queue_size=8, queue_wait=1.0
    )

    async with handler.running():
        with _core_stuck_on_large_payloads(tmp_path / "raw-data") as received:
            # More than the socket buffer, so its sender waits for a reader that never comes.
            await _forward(handler, b"x" * 1024 * 1024)
            await _forward(handler, b"small")
            data = await asyncio.to_thread(received.get, timeout=2.0)

    assert data.endswith(b"\nsmall")


@pytest.mark.asyncio
async def test_a_stalled_core_gets_forwards_refused_at_once(tmp_path: Path) -> None:
    core = tmp_path / "raw-data"
    handler = ForwardMonitoringDataHandler(
        data_socket=core, socket_timeout=0.2, queue_size=8, queue_wait=1.0, stall_pause=10.0
    )

    with create_busy_socket(socket_path=str(core), busy_for=10.0):
        async with handler.running():
            await _forward(handler, b"payload")
            await asyncio.sleep(0.5)  # past the socket timeout of that hand-over
            with pytest.raises(ForwardRefusedError):
                await _forward(handler, b"payload")


@pytest.mark.asyncio
async def test_a_refusal_during_the_stall_pause_is_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    core = tmp_path / "raw-data"
    handler = ForwardMonitoringDataHandler(
        data_socket=core, socket_timeout=0.2, queue_size=8, queue_wait=1.0, stall_pause=10.0
    )

    with create_busy_socket(socket_path=str(core), busy_for=10.0):
        async with handler.running():
            await _forward(handler, b"payload")
            await asyncio.sleep(0.5)  # past the socket timeout of that hand-over
            with caplog.at_level(logging.ERROR), pytest.raises(ForwardRefusedError):
                await _forward(handler, b"payload")

    assert "Refused monitoring data of host from relay relay" in caplog.text


@pytest.mark.asyncio
async def test_a_stall_drops_the_queued_forwards(tmp_path: Path) -> None:
    """They would reach the core minutes late, one socket timeout after another."""
    core = tmp_path / "raw-data"
    handler = ForwardMonitoringDataHandler(
        data_socket=core, socket_timeout=0.2, queue_size=16, queue_wait=1.0, stall_pause=10.0
    )

    # Busy for longer than two rounds of hand-overs, so a third would get through.
    with create_busy_socket(socket_path=str(core), busy_for=0.5) as mock_core:
        async with handler.running():
            for _ in range(12):
                await _forward(handler, b"payload")
            await asyncio.sleep(1.0)

    assert mock_core.data_queue.empty()


@pytest.mark.asyncio
async def test_forwards_are_taken_again_after_the_stall_pause(tmp_path: Path) -> None:
    core = tmp_path / "raw-data"
    handler = ForwardMonitoringDataHandler(
        data_socket=core, socket_timeout=0.2, queue_size=8, queue_wait=1.0, stall_pause=0.3
    )

    with create_busy_socket(socket_path=str(core), busy_for=0.3) as mock_core:
        async with handler.running():
            await _forward(handler, b"lost")
            await asyncio.sleep(1.0)  # past the stall and the pause after it
            await _forward(handler, b"after")
            received = await asyncio.to_thread(mock_core.data_queue.get, timeout=2.0)

    assert received.data.endswith(b"\nafter")


async def _forward(handler: ForwardMonitoringDataHandler, payload: bytes) -> None:
    await handler.process(
        relay_id=RelayID("relay"),
        payload=payload,
        host="host",
        config_serial=Serial(1),
        timestamp=0,
        service="Check_MK",
        payload_type=PayloadType.FETCHER,
    )
