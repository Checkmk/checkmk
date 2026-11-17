#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import concurrent.futures
import contextlib
import socket
import time
from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Final, NamedTuple, Self

from cmk.agent_receiver.lib.log import logger
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
from cmk.relay_protocols.monitoring_data import PayloadType

# The token the core expects in the header. Mapped explicitly rather than derived
# from the enum, so adding a payload type cannot silently produce a header the
# core does not understand.
_HEADER_TOKEN: Final[Mapping[PayloadType, str]] = {
    PayloadType.FETCHER: "fetcher",
    PayloadType.ACTIVE_CHECK: "active_check",
}


_CONNECT_RETRY_FIRST_PAUSE: Final = 0.01
_CONNECT_RETRY_MAX_PAUSE: Final = 0.2


class FailedToSendMonitoringDataError(Exception):
    pass


class _CoreStalledError(FailedToSendMonitoringDataError):
    pass


class ForwardRefusedError(Exception):
    pass


# A payload larger than the socket buffer keeps its sender waiting until the core has read
# it. Against a core that reads slowly, one sender delivered a quarter of what four did, and
# four matched the shared pool they replace (relay benchmark, test_forward_throughput).
_SENDERS: Final = 4
_QUEUE_SIZE: Final = 256
# Below the relay's 5 s request timeout, so it gets the 503 rather than giving up first.
_QUEUE_WAIT: Final = 4.0


class _Forward(NamedTuple):
    relay_id: RelayID
    host: str
    data: bytes


class _CoreQueue:
    """The forwards waiting for a sender; refuses all of them for a pause after a stall.

    Dropping the queue and refusing new forwards belong together: a forward queued
    during the pause would only meet the stalled core again.
    """

    def __init__(self, *, size: int, wait: float, pause: float) -> None:
        self._queue: Final = asyncio.Queue[_Forward](maxsize=size)
        self._wait: Final = wait
        self._pause: Final = pause
        self._paused_until = 0.0

    def __len__(self) -> int:
        return self._queue.qsize()

    async def put(self, forward: _Forward) -> None:
        if time.monotonic() < self._paused_until:
            raise ForwardRefusedError("The core takes no monitoring data at the moment")
        try:
            async with asyncio.timeout(self._wait):
                await self._queue.put(forward)
        except TimeoutError:
            logger.warning(
                "Refused monitoring data of %(host)s from relay %(relay_id)s: "
                "%(queued)d hand-overs to the core are queued",
                {"host": forward.host, "relay_id": forward.relay_id, "queued": len(self)},
            )
            raise ForwardRefusedError("Too much monitoring data is waiting for the core") from None

    async def get(self) -> _Forward:
        return await self._queue.get()

    def stall(self) -> int | None:
        """Drop the queue and pause; the number dropped, or None if already paused

        A stall during the pause extends it. Only the hand-overs already under way can
        stall then, so a core that recovered is paused for at most one socket timeout
        more.
        """
        paused_already = time.monotonic() < self._paused_until
        self._paused_until = time.monotonic() + self._pause
        dropped = 0
        while not self._queue.empty():
            self._queue.get_nowait()
            dropped += 1
        return None if paused_already else dropped


class ForwardMonitoringDataHandler:
    """Hands monitoring data to the core from a few threads, behind a bounded queue.

    The core serves a limited number of connections, and a hand-over waits for a free
    one. Only the sender threads wait, so a stalled core no longer takes the threads
    every other request needs. A forward is answered once it is queued: the relay drops
    an item on any error and never retries, so waiting for the delivery bought nothing.

    A hand-over that times out drops the queue and refuses forwards for a pause. Queued,
    they would reach the core one socket timeout after another, minutes late, while the
    relay believed them delivered; refused, the relay logs each one it drops.
    """

    def __init__(
        self,
        *,
        data_socket: Path,
        socket_timeout: float,
        queue_size: int = _QUEUE_SIZE,
        queue_wait: float = _QUEUE_WAIT,
        stall_pause: float = 5.0,
    ) -> None:
        self._data_socket: Final = data_socket
        self._socket_timeout: Final = socket_timeout
        self._stall_pause: Final = stall_pause
        self._queue: Final = _CoreQueue(size=queue_size, wait=queue_wait, pause=stall_pause)

    @contextlib.asynccontextmanager
    async def running(self) -> AsyncIterator[Self]:
        """On exit the queue is dropped, but a hand-over in progress finishes."""
        senders = [
            asyncio.create_task(self._send_queued(), name="core-sender") for _ in range(_SENDERS)
        ]
        try:
            yield self
        finally:
            for sender in senders:
                sender.cancel()
            for sender in senders:
                with contextlib.suppress(asyncio.CancelledError):
                    await sender

    async def process(
        self,
        *,
        relay_id: RelayID,
        payload: bytes,
        host: str,
        config_serial: Serial,
        timestamp: int,
        service: str,
        payload_type: PayloadType,
    ) -> None:
        header = (
            f"payload_type:{_HEADER_TOKEN[payload_type]};"
            f"payload_size:{len(payload)};"
            f"config_serial:{config_serial};"
            f"relay_id:{relay_id};"
            f"start_timestamp:{timestamp};"
            f"host_by_name:{host};"
            f"service_description:{service};"
            f"\n"
        )
        await self._queue.put(_Forward(relay_id, host, header.encode("utf-8") + payload))

    async def _send_queued(self) -> None:
        loop = asyncio.get_running_loop()
        # Leaving the block on cancellation waits for the thread, up to the socket timeout.
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="core-sender"
        ) as sender:
            while True:
                forward = await self._queue.get()
                try:
                    await loop.run_in_executor(sender, self._send_to_cmc, forward.data)
                except _CoreStalledError as e:
                    self._core_stalled(forward, e)
                except FailedToSendMonitoringDataError as e:
                    logger.error(
                        "Failed to forward monitoring data of %(host)s from relay "
                        "%(relay_id)s to the core: %(error)s (%(queued)d queued)",
                        {
                            "host": forward.host,
                            "relay_id": forward.relay_id,
                            "error": e,
                            "queued": len(self._queue),
                        },
                    )
                except Exception:
                    # Nothing restarts this task: if it ended, every later forward would
                    # wait for a free slot and get a 503 until the worker restarts.
                    logger.exception(
                        "Unexpected error forwarding monitoring data of %(host)s from relay "
                        "%(relay_id)s to the core",
                        {"host": forward.host, "relay_id": forward.relay_id},
                    )

    def _core_stalled(self, forward: _Forward, error: _CoreStalledError) -> None:
        if (dropped := self._queue.stall()) is None:
            return
        logger.error(
            "The core took no monitoring data of %(host)s from relay %(relay_id)s within "
            "%(timeout)s s: %(error)s. Dropped %(dropped)d queued forwards, refusing new "
            "ones for %(pause)s s",
            {
                "host": forward.host,
                "relay_id": forward.relay_id,
                "timeout": self._socket_timeout,
                "error": error,
                "dropped": dropped,
                "pause": self._stall_pause,
            },
        )

    def _send_to_cmc(self, data: bytes) -> None:
        """
        Send monitoring data to CMC using the UNIX socket defined by raw_data_socket.
        Args:
            data: The monitoring data to send as bytes.
        Raises:
            FailedToSendMonitoringDataError: If the socket connection or send fails.
        """
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(self._socket_timeout)
                self._connect(sock)
                sock.sendall(data)

                # See https://docs.python.org/3/library/socket.html#socket.socket.close
                # Note: close() releases the resource associated with a connection
                # but does not necessarily close the connection immediately.
                # If you want to close the connection in a timely fashion, call shutdown() before close().
                sock.shutdown(socket.SHUT_RDWR)
        # A backlog that stayed full, or a send the core did not read.
        except (BlockingIOError, TimeoutError) as e:
            raise _CoreStalledError(str(e)) from e
        except OSError as e:
            raise FailedToSendMonitoringDataError(str(e)) from e

    def _connect(self, sock: socket.socket) -> None:
        """Connect, waiting up to the socket timeout for a free slot in the backlog of the core

        The core serves a limited number of connections at once, further ones wait in its
        backlog. A socket with a timeout connects non-blocking, so a full backlog fails at
        once with EAGAIN instead of waiting.
        """
        deadline = time.monotonic() + self._socket_timeout
        pause = _CONNECT_RETRY_FIRST_PAUSE
        while True:
            try:
                sock.connect(str(self._data_socket))
                return
            except BlockingIOError:
                if (remaining := deadline - time.monotonic()) <= 0:
                    raise
                time.sleep(min(pause, remaining))
                pause = min(pause * 2, _CONNECT_RETRY_MAX_PAUSE)
