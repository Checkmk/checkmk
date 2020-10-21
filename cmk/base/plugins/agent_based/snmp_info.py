#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple
from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    SNMPStringTable,
    InventoryResult,
)

from .agent_based_api.v1 import (
    exists,
    HostLabel,
    register,
    Result,
    Service,
    SNMPTree,
    State,
    Attributes,
)


class SNMPInfo(NamedTuple):
    description: str
    contact: str
    name: str
    location: str


def parse_snmp_info(string_table: SNMPStringTable) -> SNMPInfo:
    return SNMPInfo(*string_table[0][0])


def host_label_snmp_info(section: SNMPInfo) -> HostLabelGenerator:
    for device_type in [
            "appliance",
            "firewall",
            "printer",
            "router",
            "sensor",
            "switch",
            "ups",
            "wlc",
    ]:
        if device_type in section.description.lower():
            yield HostLabel("cmk/device_type", device_type)
            return


register.snmp_section(
    name="snmp_info",
    parse_function=parse_snmp_info,
    host_label_function=host_label_snmp_info,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=["1", "4", "5", "6"],
        ),
    ],
    detect=exists(".1.3.6.1.2.1.1.1.0"),
)


def discover_snmp_info(section: SNMPInfo) -> DiscoveryResult:
    yield Service()


def check_snmp_info(section: SNMPInfo) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"{section.name}, {section.location}, {section.contact}",
        details=f"{section.description}, {section.name}, {section.location}, {section.contact}",
    )


register.check_plugin(
    name="snmp_info",
    service_name="SNMP Info",
    discovery_function=discover_snmp_info,
    check_function=check_snmp_info,
)


def inventory_snmp_info(section: SNMPInfo) -> InventoryResult:
    yield Attributes(path=["hardware", "system"],
                     inventory_attributes={
                         "product": section.description,
                     })

    yield Attributes(path=["software", "configuration", "snmp_info"],
                     inventory_attributes={
                         "contact": section.contact,
                         "name": section.name,
                         "location": section.location,
                     })


register.inventory_plugin(
    name="snmp_info",
    inventory_function=inventory_snmp_info,
)
