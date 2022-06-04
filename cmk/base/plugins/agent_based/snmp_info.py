#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional

from .agent_based_api.v1 import Attributes, exists, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, InventoryResult, StringTable
from .utils.device_types import get_device_type_label


class SNMPInfo(NamedTuple):
    description: str
    object_id: str
    contact: str
    name: str
    location: str


def _parse_string(val):
    return val.strip().replace("\r\n", " ").replace("\n", " ")


def parse_snmp_info(string_table: StringTable) -> Optional[SNMPInfo]:
    if not string_table:
        return None
    snmp_info = [_parse_string(s) for s in string_table[0]]
    return SNMPInfo(*snmp_info)


register.snmp_section(
    name="snmp_info",
    parse_function=parse_snmp_info,
    host_label_function=get_device_type_label,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    detect=exists(".1.3.6.1.2.1.1.1.0"),
)


def discover_snmp_info(section: SNMPInfo) -> DiscoveryResult:
    yield Service()


def check_snmp_info(section: SNMPInfo) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"{section.description}, {section.name}, {section.location}, {section.contact}",
    )


register.check_plugin(
    name="snmp_info",
    service_name="SNMP Info",
    discovery_function=discover_snmp_info,
    check_function=check_snmp_info,
)


def inventory_snmp_info(section: SNMPInfo) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "product": section.description,
        },
    )

    yield Attributes(
        path=["software", "configuration", "snmp_info"],
        inventory_attributes={
            "contact": section.contact,
            "name": section.name,
            "location": section.location,
        },
    )

    descr_short = section.description.split()
    descr_long = section.description.split(",")

    # Cisco devices:
    if "cisco" in section.description.lower():
        yield Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": descr_long[0],
                **(
                    {"version": (descr_short[descr_short.index("Version") + 1]).replace(",", "")}
                    if "Version" in descr_short
                    else {}
                ),
            },
        )

    # Fireeye Devices
    if "linux" in section.description.lower() and ".1.3.6.1.4.1.25597.1" in section.object_id:
        yield Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": descr_short[0],
                "kernel_version": descr_short[2],
                "arch": descr_short[-1],
            },
        )


register.inventory_plugin(
    name="snmp_info",
    inventory_function=inventory_snmp_info,
)
