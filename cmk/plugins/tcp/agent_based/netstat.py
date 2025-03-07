#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast

from cmk.agent_based.v2 import AgentSection, CheckPlugin, StringTable
from cmk.plugins.tcp.lib.models import Connection, ConnectionState, Protocol, Section
from cmk.plugins.tcp.lib.netstat import (
    check_netstat_generic,
    discover_netstat_never,
    split_ip_address,
)

# Example output from agent (Linux) - note missing LISTENING column for UDP
# <<netstat>>>
# tcp        0      0 0.0.0.0:6556            0.0.0.0:*               LISTENING
# tcp        0      0 127.0.0.1:445           0.0.0.0:*               LISTENING
# tcp        0      0 10.1.1.50:445           0.0.0.0:*               LISTENING
# tcp        0      0 127.0.0.1:57573         127.0.0.1:80            ESTABLISHED
# tcp        0      0 10.1.1.50:38692         178.248.246.154:993     ESTABLISHED
# tcp        0      0 127.0.0.1:34929         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:34922         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:80            127.0.0.1:57454         TIME_WAIT
# tcp        0      0 127.0.0.1:35005         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 10.1.1.50:38612         178.248.246.154:993     ESTABLISHED
# tcp        0      0 127.0.0.1:80            127.0.0.1:57548         TIME_WAIT
# tcp        0      0 127.0.0.1:34981         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:54552         127.0.0.1:13419         ESTABLISHED
# tcp        0      0 127.0.0.1:35012         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:34910         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:34915         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:80            127.0.0.1:57546         TIME_WAIT
# tcp        0      0 127.0.0.1:34935         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:34984         127.0.0.1:5000          TIME_WAIT
# tcp        0      0 127.0.0.1:80            127.0.0.1:57488         TIME_WAIT
# tcp        0      0 127.0.0.1:34967         127.0.0.1:5000          TIME_WAIT
# udp        0      0 10.1.2.255:137          0.0.0.0:*
# udp        0      0 10.1.2.160:137          0.0.0.0:*
# udp        0      0 0.0.0.0:137             0.0.0.0:*

# Example output from agent (Linux) - note different format of `ss` command
# udp   UNCONN    0      0                    0.0.0.0:53403              0.0.0.0:*
# udp   UNCONN    0      0                    0.0.0.0:54223              0.0.0.0:*
# tcp   TIME-WAIT 0      0             10.230.254.109:8280            172.17.0.3:39484
# tcp   LISTENING    0      64                      [::]:2049                  [::]:*

# Example Output for AIX:
# tcp4  0   0   127.0.0.1.1234  127.0.0.1.5678  ESTABLISHED
STATE_TRANSLATIONS: dict[str, str] = {
    "LISTEN": "LISTENING",  # for Ubuntu
    "ESTAB": "ESTABLISHED",  # for Ubuntu
}


def parse_netstat(string_table: StringTable) -> Section:
    try:
        is_netstat_format = string_table[1][1].isdecimal()
    except IndexError:
        # Assuming that "old" netstat format should precedence
        is_netstat_format = True

    connections = []
    for line in string_table:
        if len(line) == 6:
            if is_netstat_format:
                proto, _recv_q, _send_q, local, remote, connstate = line
            else:
                proto, connstate, _recv_q, _send_q, local, remote = line
            if proto.startswith("tcp"):  # also tcp4 and tcp6
                proto = "TCP"
            elif proto.startswith("udp"):
                proto = "UDP"
                connstate = "LISTENING"
            # Ubuntu recently deviced to use "LISTEN" instead of "LISTENING"
            if connstate == "LISTEN":
                connstate = "LISTENING"
            if connstate == "ESTAB":
                connstate = "ESTABLISHED"

        if len(line) == 5:
            proto, _recv_q, _send_q, local, remote = line
            proto = "UDP"
            connstate = "LISTENING"

        if len(line) == 3:
            # Solaris systems output a different format for udp (3 elements instead 5)
            proto, local, remote = line
            _recv_q, _send_q = "0", "0"
            proto = "UDP"
            connstate = "LISTENING"

        # Translate special representations of state strings (e.g. abbreviations into full length)
        connstate = STATE_TRANSLATIONS.get(connstate, connstate)
        # The output of `ss` contains a "-" instead of "_" in state strings.
        connstate = connstate.replace("-", "_")

        connections.append(
            Connection(
                proto=cast(Protocol, proto),
                local_address=split_ip_address(local),
                remote_address=split_ip_address(remote),
                state=ConnectionState[connstate],
            )
        )
    return connections


agent_section_netstat = AgentSection(name="netstat", parse_function=parse_netstat)
check_plugin_netstat = CheckPlugin(
    name="netstat",
    service_name="TCP Connection %s",
    discovery_function=discover_netstat_never,
    check_function=check_netstat_generic,
    check_ruleset_name="tcp_connections",
    check_default_parameters={"min_states": ("no_levels", None), "max_states": ("no_levels", None)},
)
