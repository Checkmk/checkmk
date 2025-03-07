#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.netstat import check_netstat_generic

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyDiscoveryResult
from cmk.agent_based.v2 import StringTable

check_info = {}

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

# Example Output for AIX:
# tcp4  0   0   127.0.0.1.1234  127.0.0.1.5678  ESTABLISHED


Section = list[tuple[str, list[str], list[str], str]]


def parse_netstat(string_table: StringTable) -> Section:
    def split_ip_address(ip_address: str) -> list[str]:
        if ":" in ip_address:
            return ip_address.rsplit(":", 1)
        return ip_address.rsplit(".", 1)

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

        if len(line) == 5:
            proto, _recv_q, _send_q, local, remote = line
            proto = "UDP"
            connstate = "LISTENING"

        connections.append((proto, split_ip_address(local), split_ip_address(remote), connstate))
    return connections


def discover_netstat_never(section: Section) -> LegacyDiscoveryResult:
    yield from ()  # can only be enforced


check_info["netstat"] = LegacyCheckDefinition(
    name="netstat",
    parse_function=parse_netstat,
    service_name="TCP Connection %s",
    discovery_function=discover_netstat_never,
    check_function=check_netstat_generic,
    check_ruleset_name="tcp_connections",
    check_default_parameters={"min_states": ("no_levels", None), "max_states": ("no_levels", None)},
)
