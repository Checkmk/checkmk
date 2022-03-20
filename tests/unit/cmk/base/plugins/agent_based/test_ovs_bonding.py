#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
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
