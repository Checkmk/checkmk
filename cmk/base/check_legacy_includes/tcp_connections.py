#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file

#############################################################################
#############################################################################
#
#   This code is already migrated. This banner is supposed to vanish
#   in the next couple of commits.
#
#############################################################################
#############################################################################

# parsed = {
#     "ESTABLISHED" : 6,
#     "BOUND"       : 17,
#     "SYN_SENT"    : 1,
#     "LISTEN"      : 10,
# }

tcp_conn_stats_default_levels = {}

map_counter_keys = {
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


def empty_stats():
    # we require all states from map_counter_keys due to the omit_zero_metrics option
    # concerning the perfdata
    return {value: 0 for value in map_counter_keys.values()}


def inventory_tcp_connections(parsed):
    if any(value != 0 for value in parsed.values()):
        return [(None, 'tcp_conn_stats_default_levels')]


def check_tcp_connections(item, params, parsed):
    if not parsed:
        yield 0, "Currently no TCP connections"
        return

    perfdata = []
    for tcp_state, tcp_count in sorted(parsed.items()):
        warn, crit = params.get(tcp_state, (None, None))

        # We must append all states (regardless of their value --> even if 0) to the perfdata list
        # due to metrics which has the option omit_zero_metrics
        perfdata.append((tcp_state, tcp_count, warn, crit))

        if tcp_count <= 0:
            continue

        infotext = "%s: %s" % (tcp_state, tcp_count)
        state = 0
        if crit is not None and tcp_count >= crit:
            state = 2
        elif warn is not None and tcp_count >= warn:
            state = 1
        if state:
            infotext += " (warn/crit at %d/%d)" % (warn, crit)
        yield state, infotext
    yield 0, '', perfdata
