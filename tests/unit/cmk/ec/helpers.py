#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import socket
import time
from typing import Any, override

from cmk.ccc.hostaddress import HostName

from cmk.ec.event import Event


class FakeStatusSocket(socket.socket):
    def __init__(self, query: bytes) -> None:
        super().__init__()
        self._query = query
        self._sent = False
        self._response = b""

    @override
    def recv(self, buflen: int, flags: int = 4711) -> bytes:
        if self._sent:
            return b""

        self._sent = True
        return self._query

    @override
    def sendall(self, b: Any, flags: int = 4711) -> None:
        self._response += b

    @override
    def close(self) -> None:
        pass

    def get_response(self) -> Any:
        response = ast.literal_eval(self._response.decode("utf-8"))
        # assert isinstance(response, list)
        return response


def new_event(attrs: Event) -> Event:
    now = time.time()
    default_event = Event(
        rule_id="815",
        text="",
        phase="open",
        count=1,
        time=now,
        first=now,
        last=now,
        comment="",
        host=HostName("test-host"),
        ipaddress="127.0.0.1",
        application="",
        pid=0,
        priority=3,
        facility=1,  # user
        match_groups=(""),
    )

    event = default_event.copy()
    event.update(attrs)
    return event
