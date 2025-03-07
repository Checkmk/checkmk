#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class ConnectionState(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    LISTENING = "LISTENING"
    SYN_SENT = "SYN_SENT"
    SYN_RECV = "SYN_RECV"
    LAST_ACK = "LAST_ACK"
    CLOSE_WAIT = "CLOSE_WAIT"
    TIME_WAIT = "TIME_WAIT"
    CLOSED = "CLOSED"
    CLOSING = "CLOSING"
    FIN_WAIT1 = "FIN_WAIT1"
    FIN_WAIT2 = "FIN_WAIT2"
    BOUND = "BOUND"


@dataclass(frozen=True)
class SplitIP:
    ip_address: str
    port: str


Protocol = Literal["TCP", "UDP"]


@dataclass(frozen=True)
class Connection:
    proto: Protocol
    local_address: SplitIP
    remote_address: SplitIP
    state: ConnectionState

    @property
    def local_ip(self) -> str:
        return self.local_address.ip_address

    @property
    def local_port(self) -> str:
        return self.local_address.port

    @property
    def remote_ip(self) -> str:
        return self.remote_address.ip_address

    @property
    def remote_port(self) -> str:
        return self.remote_address.port


Section = list[Connection]
