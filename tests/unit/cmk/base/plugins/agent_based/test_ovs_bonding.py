#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import ovs_bonding

DATA = [
    ["[bond1]"],
    ["bond_mode", " active-backup"],
    ["lacp", " off"],
    ["bond-detect-mode", " carrier"],
    ["updelay", " 31000 ms"],
    ["downdelay", " 200 ms"],
    #
    ["slave eth5", " enabled"],
    #
    ["slave eth1", " enabled"],
    ["active slave"],
]


def test_parse_failover() -> None:
    assert ovs_bonding.parse_ovs_bonding(DATA) == {
        "bond1": {
            "active": "eth1",
            "interfaces": {
                "eth1": {"status": "up"},
                "eth5": {"status": "up"},
            },
            "mode": "active-backup",
            "status": "up",
        },
    }


# Open vSwitch renamed `slave` to `member`, see https://github.com/openvswitch/ovs/blob/main/NEWS
DATA_MEMBER = [
    ["[ovs-bond-uplink]"],
    ["---- ovs-bond-uplink ----"],
    ["bond_mode", " balance-tcp"],
    ["bond may use recirculation", " yes, Recirc-ID ", " 1"],
    ["bond-hash-basis", " 0"],
    ["lb_output action", " disabled, bond-id", " -1"],
    ["updelay", " 0 ms"],
    ["downdelay", " 0 ms"],
    ["next rebalance", " 9989 ms"],
    ["lacp_status", " negotiated"],
    ["lacp_fallback_ab", " false"],
    ["active-backup primary", " <none>"],
    ["active member mac", " 48", "df", "37", "68", "4f", "30(eth2)"],
    #
    ["member eth2", " enabled"],
    ["active member"],
    ["may_enable", " true"],
    #
    ["member eth7", " enabled"],
    ["may_enable", " true"],
]


def test_parse_member_terminology() -> None:
    assert ovs_bonding.parse_ovs_bonding(DATA_MEMBER) == {
        "ovs-bond-uplink": {
            "active": "eth2",
            "interfaces": {
                "eth2": {"status": "up"},
                "eth7": {"status": "up"},
            },
            "mode": "balance-tcp",
            "status": "up",
        },
    }
