#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict
from .agent_based_api.v1.type_defs import AgentStringTable

from .agent_based_api.v1 import register

TCPConnections = Dict[str, int]

MAP_COUNTER_KEYS = {
    1: "ESTABLISHED",  # connection up and passing data
    2: "SYN_SENT",  # session has been requested by us; waiting for reply from remote endpoint
    3: "SYN_RECV",  # session has been requested by a remote endpoint for a socket on which we were listening
    4: "FIN_WAIT1",  # our socket has closed; we are in the process of tearing down the connection
    5: "FIN_WAIT2",  # the connection has been closed; our socket is waiting for the remote endpoint to shut down
    6: "TIME_WAIT",  # socket is waiting after closing for any packets left on the network
    7: "CLOSED",  # socket is not being used (FIXME. What does mean?)
    8: "CLOSE_WAIT",  # remote endpoint has shut down; the kernel is waiting for the application to close the socket
    9: "LAST_ACK",  # our socket is closed; remote endpoint has also shut down; we are waiting for a final acknowledgement
    10: "LISTEN",  # represents waiting for a connection request from any remote TCP and port
    11: "CLOSING",  # our socket is shut down; remote endpoint is shut down; not all data has been sent
}


def empty_stats() -> TCPConnections:
    # we require all states from map_counter_keys due to the omit_zero_metrics option
    # concerning the perfdata
    return {value: 0 for value in MAP_COUNTER_KEYS.values()}


def parse_tcp_conn_stats(string_table: AgentStringTable) -> TCPConnections:
    """
        >>> from pprint import pprint
        >>> pprint(parse_tcp_conn_stats([
        ...     ["01", "29"],
        ...     ["02", "3"],
        ...     ["0A", "26"],
        ...     ["05", "1"],
        ...     ["06", "187"],
        ... ]))
        {'CLOSED': 0,
         'CLOSE_WAIT': 0,
         'CLOSING': 0,
         'ESTABLISHED': 29,
         'FIN_WAIT1': 0,
         'FIN_WAIT2': 1,
         'LAST_ACK': 0,
         'LISTEN': 26,
         'SYN_RECV': 0,
         'SYN_SENT': 3,
         'TIME_WAIT': 187}

        >>> pprint(parse_tcp_conn_stats([
        ...     ["LISTEN", "39"],
        ...     ["IDLE", "3"],
        ...     ["TIME_WAIT", "1"],
        ...     ["ESTABLISHED", "68"],
        ...     ["BOUND", "1"],
        ... ]))
        {'BOUND': 1,
         'CLOSED': 0,
         'CLOSE_WAIT': 0,
         'CLOSING': 0,
         'ESTABLISHED': 68,
         'FIN_WAIT1': 0,
         'FIN_WAIT2': 0,
         'IDLE': 3,
         'LAST_ACK': 0,
         'LISTEN': 39,
         'SYN_RECV': 0,
         'SYN_SENT': 0,
         'TIME_WAIT': 1}

    """
    section = empty_stats()  # TODO: use counter
    for tcp_state, count, *_ in string_table:
        if len(tcp_state) == 2:
            try:
                tcp_state = MAP_COUNTER_KEYS[int(tcp_state, 16)]  # Hex
            except KeyError:
                continue
        try:
            section[tcp_state] = int(count)
        except ValueError:
            pass
    return section


register.agent_section(
    name="tcp_conn_stats",
    parse_function=parse_tcp_conn_stats,
)
