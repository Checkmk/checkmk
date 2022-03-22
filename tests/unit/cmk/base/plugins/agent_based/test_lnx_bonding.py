#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import lnx_bonding

DATA_FAILOVER = [
    ["==> ./bond0 <=="],
    ["Ethernet Channel Bonding Driver", " v5.13.19-5-pve"],
    #
    ["Bonding Mode", " fault-tolerance (active-backup)"],
    ["Primary Slave", " None"],
    ["Currently Active Slave", " enp129s0f2"],
    ["MII Status", " up"],
    ["MII Polling Interval (ms)", " 100"],
    ["Up Delay (ms)", " 200"],
    ["Down Delay (ms)", " 200"],
    ["Peer Notification Delay (ms)", " 0"],
    #
    ["Slave Interface", " enp129s0f2"],
    ["MII Status", " up"],
    ["Speed", " 10000 Mbps"],
    ["Duplex", " full"],
    ["Link Failure Count", " 0"],
    ["Permanent HW addr", " 3c", "ec", "ef", "28", "4a", "56"],
    ["Slave queue ID", " 0"],
    #
    ["Slave Interface", " enp129s0f3"],
    ["MII Status", " up"],
    ["Speed", " 10000 Mbps"],
    ["Duplex", " full"],
    ["Link Failure Count", " 0"],
    ["Permanent HW addr", " 3c", "ec", "ef", "28", "4a", "57"],
    ["Slave queue ID", " 0"],
]


def test_parse_failover() -> None:
    assert lnx_bonding.parse_lnx_bonding(DATA_FAILOVER) == {
        "bond0": {
            "active": "enp129s0f2",
            "interfaces": {
                "enp129s0f2": {"failures": 0, "hwaddr": "3C:EC:EF:28:4A:56", "status": "up"},
                "enp129s0f3": {"failures": 0, "hwaddr": "3C:EC:EF:28:4A:57", "status": "up"},
            },
            "mode": "fault-tolerance",
            "primary": "None",
            "status": "up",
        },
    }
