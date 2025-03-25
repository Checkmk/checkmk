#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.agent_based import ovs_bonding

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


def test_parse_missing_slave_interfaces() -> None:
    string_table = [["[bond1]"], ["bond_mode", " active-backup"]]
    assert not ovs_bonding.parse_ovs_bonding(string_table)


def test_parse_missing_header() -> None:
    string_table = [["bond_mode", " active-backup"]]
    with pytest.raises(ovs_bonding.InvalidOvsBondingStringTable):
        assert ovs_bonding.parse_ovs_bonding(string_table)


def test_parse_missing_slave_interface_with_active() -> None:
    string_table = [["[bond1]"], ["active slave"]]
    with pytest.raises(ovs_bonding.InvalidOvsBondingStringTable):
        assert ovs_bonding.parse_ovs_bonding(string_table)


def test_parse_missing_slave_interface_in_second_bond() -> None:
    string_table = [*DATA, ["[bond2]"], ["active slave"]]
    with pytest.raises(ovs_bonding.InvalidOvsBondingStringTable):
        assert ovs_bonding.parse_ovs_bonding(string_table)


def test_parse_missing_bond_mode() -> None:
    string_table = [["[bond1]"], ["slave eth5", " enabled"], ["active slave"]]
    with pytest.raises(KeyError):
        assert ovs_bonding.parse_ovs_bonding(string_table)
