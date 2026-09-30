#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.stormshield.agent_based.stormshield_packets import (
    check_stormshield_packets,
    discover_stormshield_packets,
    parse_stormshield_packets,
)


def test_discover_stormshield_packets_with_empty_counters() -> None:
    # Crash group 4893: an SSL VPN interface reports empty packet counters
    section = parse_stormshield_packets(
        [
            ["out", "eth0", "Ethernet", "1000", "10", "5", "3", "2"],
            ["sslvpn_udp", "sslvpn1", "sslvpn", "", "", "", "0", "0"],
        ]
    )
    assert list(discover_stormshield_packets(section)) == [Service(item="out")]


def test_check_stormshield_packets_with_empty_counters() -> None:
    section = parse_stormshield_packets(
        [["out", "eth0", "Ethernet", "", "10", "", "3", "2"]],
    )
    assert list(check_stormshield_packets("out", section)) == [
        Result(
            state=State.UNKNOWN,
            summary="No value received for: accepted packets, ICMP packets (expected integer)",
        )
    ]
