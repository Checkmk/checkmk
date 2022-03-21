#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import bonding

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

_ParsedBlocks = tuple[dict[str, str], Sequence[dict[str, str]], dict[str, str]]


def _split_bonds(string_table: StringTable) -> Mapping[str, StringTable]:
    bonds: dict[str, list[list[str]]] = {}
    for line in string_table:
        if len(line) == 1 and line[0].startswith("/"):
            continue

        line = [i.strip() for i in line]

        words = line[0].split()
        if words[0] == "==>":
            current = bonds.setdefault(words[1].lstrip(".").lstrip("/"), [])
        elif "Channel Bonding Driver" in line:
            pass
        else:
            current.append(line)
    return bonds


def _parse_blocks(bond_lines: StringTable) -> _ParsedBlocks:
    main: dict[str, str] = {}
    interfaces: list[dict[str, str]] = []
    info8023ad: dict[str, str] = {}

    # start with global part
    current = main
    for key, *values in bond_lines:
        # check for start of new sections
        if key == "Slave Interface":
            current = {}
            interfaces.append(current)
        elif key == "802.3ad info":
            current = info8023ad

        current[key] = ":".join(values)

    return main, interfaces, info8023ad


def _convert_to_generic(bonds: Mapping[str, _ParsedBlocks]) -> bonding.Section:
    """convert to generic dict, also used by other bonding checks"""
    converted: dict[str, bonding.Bond] = {}
    for name, (main, interfaces, info8023ad) in bonds.items():
        new_interfaces: dict[str, bonding.Interface] = {}
        for interface in interfaces:
            eth = interface["Slave Interface"]
            new_interfaces[eth] = {
                "status": interface["MII Status"],
                "hwaddr": interface.get("Permanent HW addr", ""),
                "failures": int(interface["Link Failure Count"]),
            }
            if "Aggregator ID" in interface:
                new_interfaces[eth]["aggregator_id"] = interface["Aggregator ID"]

        this_bond: bonding.Bond = {
            "status": main["MII Status"],
            "mode": main["Bonding Mode"].split("(")[0].strip(),
            "interfaces": new_interfaces,
        }
        if "Aggregator ID" in info8023ad:
            this_bond["aggregator_id"] = info8023ad["Aggregator ID"]

        if "Currently Active Slave" in main:
            this_bond["active"] = main["Currently Active Slave"]
        if "Primary Slave" in main:
            this_bond["primary"] = main["Primary Slave"].split()[0]

        converted[name] = this_bond

    return converted


def parse_lnx_bonding(string_table: StringTable) -> bonding.Section:
    return _convert_to_generic({k: _parse_blocks(v) for k, v in _split_bonds(string_table).items()})


register.agent_section(
    name="lnx_bonding",
    parsed_section_name="bonding",
    parse_function=parse_lnx_bonding,
)
