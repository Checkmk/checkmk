#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, List
from .agent_based_api.v1 import (
    exists,
    OIDEnd,
    HostLabel,
    register,
    SNMPTree,
)

from .agent_based_api.v1.type_defs import (
    StringTable,
    HostLabelGenerator,
)

from .utils.device_types import is_fibrechannel_switch, SNMPDeviceType


class SNMPExtendedInfo(NamedTuple):
    oid_end: str
    entPhysDescr: str
    entPhysContainedIn: str
    entPhysClass: str
    entPhysName: str
    entPhysSoftwareRev: str
    entPhysSerialNum: str
    entPhysMfgName: str
    entPhysModelName: str


def parse_snmp_extended_info(string_table: List[StringTable]) -> List[SNMPExtendedInfo]:
    return [SNMPExtendedInfo(*entry) for entry in string_table[0]]


def host_label_snmp_extended_info(section: List[SNMPExtendedInfo]) -> HostLabelGenerator:
    if not section:
        return
    for device_type in SNMPDeviceType:
        if device_type.name in section[0].entPhysDescr.upper():
            if device_type is SNMPDeviceType.SWITCH and is_fibrechannel_switch(
                    section[0].entPhysDescr):
                yield HostLabel("cmk/device_type", "fcswitch")
            else:
                yield HostLabel("cmk/device_type", device_type.name.lower())
            return


register.snmp_section(
    name="snmp_extended_info",
    parse_function=parse_snmp_extended_info,
    host_label_function=host_label_snmp_extended_info,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[
                OIDEnd(),
                "2",  # entPhysicalDescr
                "4",  # entPhysicalContainedIn
                "5",  # entPhysicalClass
                "7",  # entPhysicalName
                "10",  # entPhysicalSoftwareRev (NEW)
                "11",  # entPhysicalSerialNum
                "12",  # entPhysicalMfgName (NEW)
                "13",  # entPhysicalModelName
            ],
        ),
    ],
    detect=exists(".1.3.6.1.2.1.47.1.1.1.1.*"),
)
