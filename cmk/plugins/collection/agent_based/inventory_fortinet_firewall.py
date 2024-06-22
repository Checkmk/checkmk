#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, MutableMapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    equals,
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)


class Interface(NamedTuple):
    if_index: str
    if_name: str
    ip_address: str
    address_type: str
    subnet: list[str]


SectionFortinetInterface = Mapping[str, Interface]

# It is possible for the same IP address to have more than one subnet.
# However, this is considered a misconfiguration that needs to be fixed.
# In the event that the same IP address has more than one subnet, the parse function may crash.
# We currently do not have any test data for this scenario.
# Once we do, the requirement is to list all subnets in the same row, separated by commas. See SUP-8642.


def parse_fortinet_firewall_network_interfaces(
    string_table: Sequence[StringTable],
) -> SectionFortinetInterface:
    if not string_table:
        return {}

    raw_interfaces, raw_interface_names = string_table
    if_names_lookup = dict(raw_interface_names)
    interface_mappings: MutableMapping[str, Interface] = {}

    for if_ip, if_index, if_subnet in raw_interfaces:
        if if_ip in interface_mappings:
            interface_mappings[if_ip].subnet.append(if_subnet)
        else:
            interface_mappings[if_ip] = Interface(
                if_index=if_index,
                if_name=if_names_lookup[if_index],
                ip_address=if_ip,
                address_type="IPv4",
                subnet=[if_subnet],
            )

    return interface_mappings


snmp_section_fortinet_firewall_network_interfaces = SNMPSection(
    name="fortinet_firewall_network_interfaces",
    parse_function=parse_fortinet_firewall_network_interfaces,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1.641"),
    fetch=[
        SNMPTree(
            # Even though this table is depricated, it is used because the subnets can only be found in it.
            # Also, only IPv4 addresses can be found in this table
            base=".1.3.6.1.2.1.4.20.1",
            oids=[
                "1",  # IP address
                "2",  # interface index
                "3",  # subnet
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",
            oids=[
                OIDEnd(),
                "1",  # interface name
            ],
        ),
    ],
)


def inventory_fortinet_firewall(section: SectionFortinetInterface) -> InventoryResult:
    for interface in section.values():
        yield TableRow(
            path=["networking", "addresses"],
            key_columns={
                "address": interface.ip_address,
            },
            inventory_columns={
                "index": interface.if_index,
                "device": interface.if_name,
                "type": interface.address_type,
                "subnet": ",".join(interface.subnet),
            },
        )


inventory_plugin_fortinet_firewall_network_interfaces = InventoryPlugin(
    name="fortinet_firewall_network_interfaces",
    inventory_function=inventory_fortinet_firewall,
)
