#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.stormshield.agent_based.stormshield_packets import (
    discover_stormshield_packets,
    parse_stormshield_packets,
)


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="Crash report 8e628742-9c97-11f1-a15d-bc241159152b: ValueError",
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
