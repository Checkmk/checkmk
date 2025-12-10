#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import socket
from pathlib import Path
from typing import Final

from cmk.agent_receiver.relay.lib.shared_types import Serial


class FailedToSendMonitoringDataError(Exception):
    pass


@dataclasses.dataclass
class ForwardMonitoringDataHandler:
    def __init__(self, data_socket: Path, socket_timeout: float = 5.0) -> None:
        self._data_socket: Path = data_socket
        self._socket_timeout: Final = socket_timeout

    def process(
        self, *, payload: bytes, host: str, config_serial: Serial, timestamp: int, service: str
    ) -> None:
        header = (
            "payload_type:fetcher;"
            f"payload_size:{len(payload)};"
            f"config_serial:{config_serial};"
            f"start_timestamp:{timestamp};"
            f"host_by_name:{host};"
            f"service_description:{service};"
            f"\n"
        )
        self._send_to_cmc(header.encode("utf-8") + payload)

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
                sock.connect(str(self._data_socket))
                sock.sendall(data)

                # See https://docs.python.org/3/library/socket.html#socket.socket.close
                # Note: close() releases the resource associated with a connection
                # but does not necessarily close the connection immediately.
                # If you want to close the connection in a timely fashion, call shutdown() before close().
                sock.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            raise FailedToSendMonitoringDataError(str(e)) from e
