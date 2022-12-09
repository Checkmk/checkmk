#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
import socket
from typing import Any


class FakeStatusSocket(socket.socket):
    def __init__(self, query: bytes) -> None:
        super().__init__()
        self._query = query
        self._sent = False
        self._response = b""

    def recv(self, buflen: int, flags: int = 4711) -> bytes:
        if self._sent:
            return b""

        self._sent = True
        return self._query

    def sendall(self, b: Any, flags: int = 4711) -> None:
        self._response += b

    def close(self) -> None:
        pass

    def get_response(self) -> Any:
        return ast.literal_eval(self._response.decode("utf-8"))
