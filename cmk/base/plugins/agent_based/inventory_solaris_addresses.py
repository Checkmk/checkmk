#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ifconfig -a
# lo0: flags=2001000849 <UP,LOOPBACK,RUNNING,MULTICAST,IPv4,VIRTUAL> mtu 8232 index 1
# inet 127.0.0.1 netmask ff000000
# ce0: flags=1000843 <UP,BROADCAST,RUNNING,MULTICAST,IPv4>mtu 1500 index 3
# inet 192.168.84.253 netmask ffffff00 broadcast 192.168.84.255
# ether 0:3:ba:7:84:5e
# bge0: flags=1004843 <UP,BROADCAST,RUNNING,MULTICAST,DHCP,IPv4>mtu 1500 index 2
# inet 10.8.57.39 netmask ffffff00 broadcast 10.8.57.255
# ether 0:3:ba:29:fc:cc

from typing import Dict, NamedTuple, Optional, Sequence, Tuple

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Interface(NamedTuple):
    idx: int
    description: str
    alias: str
    speed: int
    phys_address: str
    port_type: int


class Address(NamedTuple):
    device: str
    address: Optional[str]
    address_type: Optional[str]


Section = Tuple[Sequence[Interface], Sequence[Address]]


def parse_solaris_addresses(string_table: StringTable) -> Section:
    parsed: Dict = {}
    dev_name = None
    for line in string_table:
        if line[0][-1] == ":":
            dev_name = line[0][:-1]
            parsed.setdefault(
                dev_name,
                {
                    "description": dev_name,
                    "index": int(line[-1]),
                },
            )
        elif "ether" in line and dev_name:
            parsed[dev_name]["phys_address"] = line[1]
        else:
            if "inet" in line and dev_name:
                parsed[dev_name]["IPv4"] = line[1]
            if "netmask" in line and dev_name:
                parsed[dev_name]["netmask"] = line[3]
            if "inet6" in line and dev_name:
                parsed[dev_name]["ipv6"] = line[1]

    interfaces = []
    addresses = []
    for device, attrs in parsed.items():
        if attrs.get("phys_address"):
            interfaces.append(
                Interface(
                    idx=attrs.get("index"),
                    description=device,
                    alias=device,
                    speed=0,
                    phys_address=attrs.get("phys_address", ""),
                    port_type=6,
                )
            )

        address: Optional[str] = None
        address_type: Optional[str] = None
        if "IPv4" in attrs:
            address = attrs["IPv4"]
            address_type = "IPv4"
        elif "IPv6" in attrs:
            address = attrs["IPv6"]
            address_type = "IPv6"

        addresses.append(
            Address(
                device=device,
                address=address,
                address_type=address_type,
            )
        )

    return interfaces, addresses


register.agent_section(
    name="solaris_addresses",
    parse_function=parse_solaris_addresses,
)


def inventory_solaris_addresses(section: Section) -> InventoryResult:
    interfaces, addresses = section

    ifaces_path = ["networking", "interfaces"]
    for iface in interfaces:
        yield TableRow(
            path=ifaces_path,
            key_columns={
                "index": iface.idx,
                "description": iface.description,
                "alias": iface.alias,
            },
            inventory_columns={
                "speed": 0,
                "phys_address": iface.phys_address,
                "port_type": 6,
            },
            status_columns={},
        )

    addresses_path = ["networking", "addresses"]
    for address in addresses:
        yield TableRow(
            path=addresses_path,
            key_columns={
                "device": address.device,
            },
            inventory_columns={
                "address": address.address,
                "type": address.address_type,
            },
            status_columns={},
        )


register.inventory_plugin(
    name="solaris_addresses",
    inventory_function=inventory_solaris_addresses,
)
