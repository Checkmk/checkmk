#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import bonding


def parse_ovs_bonding(string_table: StringTable) -> bonding.Section:
    bonds: dict[str, dict[str, str]] = {}
    bonds_interfaces: dict[str, dict[str, bonding.Interface]] = {}
    for line in string_table:
        if line[0][0] == "[":
            bond = line[0][1:-1]
            bonds[bond] = {}
        elif len(line) == 2:
            left = line[0]
            right = line[1].strip()
            if left.startswith("slave"):
                eth = left.split()[1]
                bonds_interfaces.setdefault(bond, {})[eth] = {
                    "status": right == "enabled" and "up" or right,
                }
                last_interface = eth
            else:
                bonds[bond][left] = right
        elif line[0] == "active slave":
            bonds[bond]["active"] = last_interface

    parsed: dict[str, bonding.Bond] = {}
    for bond, status in bonds.items():
        all_down = True
        if not status.get("active"):
            continue
        for st in bonds_interfaces[bond].values():
            if st["status"] == "up":
                all_down = False
                break

        parsed[bond] = {
            "status": all_down and "down" or "up",
            "active": status["active"],
            "mode": status["bond_mode"],
            "interfaces": bonds_interfaces[bond],
        }

    return parsed


register.agent_section(
    name="ovs_bonding",
    parsed_section_name="bonding",
    parse_function=parse_ovs_bonding,
)
