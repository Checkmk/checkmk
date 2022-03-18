#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, TypedDict

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable

# <<<lnx_bonding:sep(58)>>>
# ==> bond0 <==
# Ethernet Channel Bonding Driver: v3.7.1 (April 27, 2011)
#
# Bonding Mode: load balancing (round-robin)
# MII Status: down
# MII Polling Interval (ms): 0
# Up Delay (ms): 0
# Down Delay (ms): 0
#
# ==> bond1 <==
# Ethernet Channel Bonding Driver: v3.2.5 (March 21, 2008)
#
# Bonding Mode: fault-tolerance (active-backup)
# Primary Slave: eth0
# Currently Active Slave: eth0
# MII Status: up
# MII Polling Interval (ms): 100
# Up Delay (ms): 0
# Down Delay (ms): 0
#
# Slave Interface: eth4
# MII Status: up
# Link Failure Count: 0
# Permanent HW addr: 00:1b:21:49:d4:e4
#
# Slave Interface: eth0
# MII Status: up
# Link Failure Count: 1
# Permanent HW addr: 00:26:b9:7d:89:2e


class _Interface(TypedDict, total=False):
    status: str
    mode: str
    hwaddr: str
    failures: int
    aggregator_id: str


class _ConvertedBond(TypedDict, total=False):
    status: str
    mode: str
    interfaces: Mapping[str, _Interface]
    aggregator_id: str
    active: str
    primary: str


SectionBonding = Mapping[str, _ConvertedBond]


def _split_bonds(string_table: StringTable) -> Mapping[str, StringTable]:
    bonds: dict[str, list[list[str]]] = {}
    for line in string_table:
        if len(line) == 1 and line[0].startswith("/"):
            continue

        line = [i.strip() for i in line]

        words = line[0].split()
        if words[0] == "==>":
            current = bonds.setdefault(words[1], [])
        elif "Channel Bonding Driver" in line:
            pass
        else:
            current.append(line)
    return bonds


# this is untypebable :-(
def _parse_bond(bond_lines: StringTable):
    bond: dict = {}
    interfaces = bond.setdefault("interfaces", {})
    # start with global part
    current = bond.setdefault("main", {})

    for line in bond_lines:
        # check for start of new sections
        if line[0] == "Slave Interface":
            current = interfaces.setdefault(line[1], {})
        elif line[0] == "802.3ad info":
            current = bond.setdefault("802.3ad info", {})
        # or add key/val to current dict
        else:
            current[line[0]] = ":".join(line[1:])
    return bond


def _convert_to_generic(bonds) -> SectionBonding:
    """convert to generic dict, also used by other bonding checks"""
    # 'bonds' is a really nasty type. At least the return type is defined for this function.
    converted: dict[str, _ConvertedBond] = {}
    for bond, status in bonds.items():
        bond = bond.lstrip("./")
        interfaces: dict[str, _Interface] = {}
        for eth, ethstatus in status["interfaces"].items():
            interfaces[eth] = {
                "status": ethstatus["MII Status"],
                "hwaddr": ethstatus.get("Permanent HW addr", ""),
                "failures": int(ethstatus["Link Failure Count"]),
            }
            if "Aggregator ID" in ethstatus:
                interfaces[eth]["aggregator_id"] = ethstatus["Aggregator ID"]

        this_bond: _ConvertedBond = {
            "status": status["main"]["MII Status"],
            "mode": status["main"]["Bonding Mode"].split("(")[0].strip(),
            "interfaces": interfaces,
        }
        if "Aggregator ID" in status.get("802.3ad info", ()):
            this_bond["aggregator_id"] = status["802.3ad info"]["Aggregator ID"]

        if "Currently Active Slave" in status["main"]:
            this_bond["active"] = status["main"]["Currently Active Slave"]
        if "Primary Slave" in status["main"]:
            this_bond["primary"] = status["main"]["Primary Slave"].split()[0]

        converted[bond] = this_bond

    return converted


def parse_lnx_bonding(string_table: StringTable) -> SectionBonding:
    return _convert_to_generic({k: _parse_bond(v) for k, v in _split_bonds(string_table).items()})


register.agent_section(
    name="lnx_bonding",
    parse_function=parse_lnx_bonding,
)
