#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import socket
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from fastapi.concurrency import run_in_threadpool

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


@dataclasses.dataclass
class ForwardMonitoringDataHandler:
    def __init__(self, data_socket: Path, socket_timeout: float = 5.0) -> None:
        self._data_socket: Path = data_socket
        self._socket_timeout: Final = socket_timeout

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
        # Off the loop: the hand-over waits for the core, up to the socket timeout.
        await run_in_threadpool(self._send_to_cmc, header.encode("utf-8") + payload)

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
        except OSError as e:
            raise FailedToSendMonitoringDataError(str(e)) from e

    def _connect(self, sock: socket.socket) -> None:
        """Connect, waiting up to the socket timeout for a free slot in the backlog of the core

        The core accepts one waiting connection at a time. A socket with a timeout connects
        non-blocking, so a full backlog fails at once with EAGAIN instead of waiting.
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
