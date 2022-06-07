#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<win_networkadapter:sep(58)>>>
# AdapterType: Ethernet 802.3
# DeviceID: 7
# MACAddress: 08:00:27:9C:F8:39
# Name: Intel(R) PRO/1000 MT-Desktopadapter
# NetworkAddresses:
# ServiceName: E1G60
# Speed: 1000000000
# Address: 192.168.178.26
# Subnet: 255.255.255.0
# DefaultGateway: 192.168.178.1

from typing import Dict, List, Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping]


def parse_win_networkadapter(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> Section:
    adapters: List[Mapping] = []
    first_varname = None
    array: Dict = {}
    addrtypes: Dict = {}

    for line in string_table:
        # return 'lost' double-colons back
        if len(line) < 2:
            continue

        stripped_line = [w.strip() for w in line]
        varname = stripped_line[0]
        value = ":".join(line[1:])

        # empty? skip!
        if not value:
            continue

        # Check whether we have a new instance
        # if we meet varname again, then we assume that this
        # is new instance
        if first_varname and varname == first_varname:
            adapters.append(array)
            array = {}
            addrtypes = {}

        if not first_varname:
            first_varname = varname

        if varname == "Name":
            array["name"] = value
        elif varname == "AdapterType":
            array["type"] = value
        elif varname == "MACAddress":
            array["macaddress"] = value
        elif varname == "Speed":
            array["speed"] = int(value)
        elif varname == "Address":
            for address in value.split(" "):
                addrtype = "ipv6" if ":" in address else "ipv4"
                addrtypes.setdefault(addrtype + "_address", []).append(address)
        elif varname == "Subnet":
            for address in value.split(" "):
                addrtype = "ipv4" if "." in address else "ipv6"
                addrtypes.setdefault(addrtype + "_subnet", []).append(address)
        elif varname == "DefaultGateway":
            array["gateway"] = value

        # address string array in comma-separated string packing: ['a1','a2',...] -> 'a1,a2...'
        for addrtype in addrtypes:
            array[addrtype] = ", ".join(addrtypes[addrtype])

    # Append last array
    if array:
        adapters.append(array)
    return adapters


register.agent_section(
    name="win_networkadapter",
    parse_function=parse_win_networkadapter,
)


def inventory_win_networkadapter(section: Section) -> InventoryResult:
    path = ["hardware", "nwadapter"]
    for adapter in sorted(section, key=lambda a: a.get("name", "")):
        if "name" in adapter:
            yield TableRow(
                path=path,
                key_columns={
                    "name": adapter["name"],
                },
                inventory_columns={
                    "type": adapter.get("type"),
                    "macaddress": adapter.get("macaddress"),
                    "speed": adapter.get("speed"),
                    "gateway": adapter.get("gateway"),
                    "ipv4_address": adapter.get("ipv4_address"),
                    "ipv6_address": adapter.get("ipv6address"),
                    "ipv4_subnet": adapter.get("ipv4_subnet"),
                    "ipv6_subnet": adapter.get("ipv6subnet"),
                },
                status_columns={},
            )


register.inventory_plugin(
    name="win_networkadapter",
    inventory_function=inventory_win_networkadapter,
)
