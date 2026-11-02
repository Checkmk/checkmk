#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import socket
from collections.abc import Callable, Iterator
from contextlib import suppress

import pytest
from starlette.types import Receive, Scope, Send
from uvicorn import Config, Server

from cmk.maps.backend.core.sse import manager
from cmk.maps.backend.server.worker import MapsWorker


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def _reopen_the_manager() -> Iterator[None]:
    yield
    manager._subscribers.clear()  # noqa: SLF001
    manager._closed = False  # noqa: SLF001


async def _stream(_scope: Scope, _receive: Receive, send: Send) -> None:
    """Stands in for a map stream."""
    subscriber = manager.subscribe("map", None)
    await send({"type": "http.response.start", "status": 200, "headers": []})
    with suppress(asyncio.QueueShutDown):
        await subscriber.queue.get()
    manager.unsubscribe("map", subscriber)
    await send({"type": "http.response.body", "body": b""})


async def _poll(done: Callable[[], object]) -> None:
    while not done():
        await asyncio.sleep(0.01)


async def _stop_a_server_with_an_open_stream() -> None:
    server = Server(
        Config(app=_stream, lifespan="off", log_config=None, **MapsWorker.CONFIG_KWARGS)
    )
    with socket.create_server(("127.0.0.1", 0)) as sock:
        serving = asyncio.create_task(server.serve(sockets=[sock]))
        await asyncio.wait_for(_poll(lambda: server.started), timeout=5)
        _, writer = await asyncio.open_connection(*sock.getsockname()[:2])
        try:
            writer.write(b"GET /stream HTTP/1.1\r\nHost: maps\r\n\r\n")
            await asyncio.wait_for(_poll(lambda: manager.get_subscriber_count("map")), timeout=5)

            server.should_exit = True
            await asyncio.wait_for(serving, timeout=5)
        finally:
            serving.cancel()
            writer.close()
            await writer.wait_closed()


def test_a_stopping_server_ends_the_open_map_streams() -> None:
    asyncio.run(_stop_a_server_with_an_open_stream())

    assert manager.get_subscriber_count("map") == 0
