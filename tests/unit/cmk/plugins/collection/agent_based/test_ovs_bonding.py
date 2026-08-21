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

SECTION = {
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


def test_parse_failover() -> None:
    assert ovs_bonding.parse_ovs_bonding(DATA) == SECTION


def test_parse_handle_header() -> None:
    """`ovs-appctl bond/show` may print `---- bond0 ----` etc."""
    assert ovs_bonding.parse_ovs_bonding(
        [
            ["[bond1]"],
            ["---- bond1 ----"],
            ["bond_mode", " balance-slb"],
            ["bond may use recirculation", " no, Recirc-ID ", " -1"],
            ["bond-hash-basis", " 0"],
            ["updelay", " 31000 ms"],
            ["downdelay", " 200 ms"],
            ["next rebalance", " 1322080 ms"],
            ["lacp_status", " off"],
            ["active slave mac", " 00", "00", "00", "00", "00", "00(eth0)"],  # modified
            ["slave eth0", " enabled"],
            ["active slave"],
            ["may_enable", " true"],
            ["hash 221", " 2679 kB load"],
            ["slave eth1", " enabled"],
            ["may_enable", " true"],
        ]
    ) == {
        "bond1": {
            "status": "up",
            "active": "eth0",
            "mode": "balance-slb",
            "interfaces": {"eth0": {"status": "up"}, "eth1": {"status": "up"}},
        }
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
    assert ovs_bonding.parse_ovs_bonding(string_table) == {}


def test_parse_missing_slave_interface_in_second_bond() -> None:
    string_table = [*DATA, ["[bond2]"], ["active slave"]]
    assert ovs_bonding.parse_ovs_bonding(string_table) == SECTION


def test_parse_missing_bond_mode() -> None:
    string_table = [["[bond1]"], ["slave eth5", " enabled"], ["active slave"]]
    with pytest.raises(KeyError):
        assert ovs_bonding.parse_ovs_bonding(string_table)
