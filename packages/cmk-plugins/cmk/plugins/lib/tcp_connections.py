#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

TCPConnections = dict[str, int]

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
