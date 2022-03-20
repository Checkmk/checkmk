#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import windows_os_bonding

DATA = [
    ["Team Name", " LAN"],
    ["Bonding Mode", " Dynamic"],
    ["Status", " Up"],
    ["Speed", " 20 Gbps"],
    #
    ["Slave Name", " NIC1"],
    ["Slave Interface", " Ethernet_14"],
    ["Slave Description", " Intel(R) Ethernet 10G 2P X520-k bNDC #2"],
    ["Slave Status", " Up"],
    ["Slave Speed", " 10 Gbps"],
    ["Slave MAC address", " 18-A9-9B-9F-AD-28"],
    #
    ["Slave Name", " NIC2"],
    ["Slave Interface", " Ethernet_10"],
    ["Slave Description", " Intel(R) Ethernet 10G 2P X520-k bNDC"],
    ["Slave Status", " Up"],
    ["Slave Speed", " 10 Gbps"],
    ["Slave MAC address", " 18-A9-9B-9F-AD-2A"],
]


def test_parse_failover() -> None:
    assert windows_os_bonding.parse_windows_os_bonding(DATA) == {
        "LAN": {
            "interfaces": {
                "NIC1": {"hwaddr": "18:a9:9b:9f:ad:28", "status": "up"},
                "NIC2": {"hwaddr": "18:a9:9b:9f:ad:2a", "status": "up"},
            },
            "mode": "Dynamic",
            "speed": "20 Gbps",
            "status": "up",
        }
    }
