#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import StrEnum


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
