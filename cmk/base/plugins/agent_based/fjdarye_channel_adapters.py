#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# pylint: disable=no-else-return

# check_mk plugin to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de

# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status
# the latter can be one of the following:

from typing import List, Mapping, MutableMapping, NamedTuple

from .agent_based_api.v1 import any_of, equals, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

FJDARYE_CHANNEL_ADAPTERS = {
    ".1.3.6.1.4.1.211.1.21.1.60": ".2.2.2.1",  # fjdarye60
    ".1.3.6.1.4.1.211.1.21.1.100": ".2.3.2.1",  # fjdarye100
    ".1.3.6.1.4.1.211.1.21.1.101": ".2.3.2.1",  # fjdarye101
    ".1.3.6.1.4.1.211.1.21.1.150": ".2.3.2.1",  # fjdarye500
}

FJDARYE_ITEM_STATUS = {
    "1": Result(state=State.OK, summary="Normal"),
    "2": Result(state=State.CRIT, summary="Alarm"),
    "3": Result(state=State.WARN, summary="Warning"),
    "4": Result(state=State.CRIT, summary="Invalid"),
    "5": Result(state=State.CRIT, summary="Maintenance"),
    "6": Result(state=State.CRIT, summary="Undefined"),
}


class FjdaryeItem(NamedTuple):
    item_index: str
    status: str


SectionFjdaryeItem = Mapping[str, FjdaryeItem]


def parse_fjdarye_item(string_table: List[StringTable]) -> SectionFjdaryeItem:
    fjdarye_items: MutableMapping[str, FjdaryeItem] = {}

    for device in string_table:
        if device:
            for item_index, status in device:
                fjdarye_items.setdefault(item_index, FjdaryeItem(item_index, status))
    return fjdarye_items


register.snmp_section(
    name="fjdarye_channel_adapters",
    parse_function=parse_fjdarye_item,
    fetch=[
        SNMPTree(base=f"{device_oid}{channel_adapter_oid}", oids=["1", "3"])
        for device_oid, channel_adapter_oid in FJDARYE_CHANNEL_ADAPTERS.items()
    ],
    detect=any_of(
        *[equals(".1.3.6.1.2.1.1.2.0", device_oid) for device_oid in FJDARYE_CHANNEL_ADAPTERS]
    ),
)

# generic inventory item - status other than 'invalid' is ok for inventory
def discover_fjdarye_item(section: SectionFjdaryeItem) -> DiscoveryResult:
    for item in section.values():
        if item.status != "4":
            yield Service(item=item.item_index)


# generic check_function returning the nagios-code and the status text
def check_fjdarye_item(item: str, section: SectionFjdaryeItem) -> CheckResult:
    if fjdarye_item := section.get(item):
        yield FJDARYE_ITEM_STATUS.get(
            fjdarye_item.status, Result(state=State.UNKNOWN, summary="Unknown")
        )


register.check_plugin(
    name="fjdarye_channel_adapters",
    service_name="Channel Adapter %s",
    discovery_function=discover_fjdarye_item,
    check_function=check_fjdarye_item,
)
