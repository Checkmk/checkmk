#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import socket
from pathlib import Path


class FailedToSendMonitoringDataError(Exception):
    pass


@dataclasses.dataclass
class ForwardMonitoringDataHandler:
    def __init__(self, data_socket: Path) -> None:
        self._data_socket = data_socket

    def process(self, payload: bytes) -> None:
        self._send_to_cmc(payload)

    def _send_to_cmc(self, data: bytes) -> None:
        """
        Send monitoring data to CMC using the UNIX socket defined by raw_data_socket.
        Args:
            data: The monitoring data to send as bytes.
        Raises:
            OSError: If the socket connection or send fails.
        """
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(str(self._data_socket))
                sock.sendall(data)
        except OSError as e:
            raise FailedToSendMonitoringDataError(str(e)) from e
