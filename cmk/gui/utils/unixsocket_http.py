#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from pathlib import Path
from typing import override

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool


def make_session(
    socket_path: Path,
    target_base_url: str,
) -> Session:
    session = Session()
    session.trust_env = False
    session.mount(
        target_base_url,
        _LocalAdapter(socket_path),
    )
    return session


class _LocalConnection(HTTPConnection):
    def __init__(self, socket_path: Path) -> None:
        super().__init__("localhost")
        self._socket_path = socket_path

    @override
    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(self._socket_path))


class _LocalConnectionPool(HTTPConnectionPool):
    def __init__(self, socket_path: Path) -> None:
        super().__init__("localhost")
        self._connection = _LocalConnection(socket_path)

    # TODO: Why does `@override` not work here?
    def _new_conn(self) -> _LocalConnection:
        return self._connection


class _LocalAdapter(HTTPAdapter):
    def __init__(self, socket_path: Path) -> None:
        super().__init__()
        self._connection_pool = _LocalConnectionPool(socket_path)

    @override
    def get_connection_with_tls_context(
        self,
        reques: object,
        verify: object,
        proxies: object = None,
        cert: object = None,
    ) -> _LocalConnectionPool:
        return self._connection_pool
