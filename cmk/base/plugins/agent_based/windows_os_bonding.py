#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import bonding


def parse_windows_os_bonding(string_table: StringTable) -> bonding.Section:
    bonds: dict[str, bonding.Bond] = {}
    bonds_interfaces: dict[str, dict[str, bonding.Interface]] = defaultdict(dict)

    for line in string_table:
        if len(line) > 1:
            item = line[1].lstrip()
        if line[0] == "Team Name":
            bond = item
            bonds[bond] = {}
            bonds[bond]["interfaces"] = {}
        elif line[0] == "Bonding Mode":
            bonds[bond]["mode"] = item
        elif line[0] == "Status":
            bonds[bond]["status"] = item.lower()
        elif line[0] == "Speed":
            bonds[bond]["speed"] = item
        elif line[0] == "Slave Name":
            slave = item
            bonds_interfaces[bond][slave] = {}
        elif line[0] == "Slave Status":
            bonds_interfaces[bond][slave]["status"] = item.lower()
        elif line[0] == "Slave MAC address":
            bonds_interfaces[bond][slave]["hwaddr"] = item.lower().replace("-", ":")

    for name, interfaces in bonds_interfaces.items():
        bonds[name]["interfaces"] = interfaces
    return bonds


register.agent_section(
    name="windows_os_bonding",
    parse_function=parse_windows_os_bonding,
)
