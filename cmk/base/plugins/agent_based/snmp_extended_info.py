#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple
from .agent_based_api.v1 import (
    exists,
    OIDEnd,
    register,
    SNMPTree,
)

from .agent_based_api.v1.type_defs import StringTable

from .utils.device_types import get_device_type_label


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


class SNMPExtendedInfoSequence(list):
    @property
    def description(self):
        return self[0].entPhysDescr


def parse_snmp_extended_info(string_table: StringTable) -> SNMPExtendedInfoSequence:
    return SNMPExtendedInfoSequence(SNMPExtendedInfo(*entry) for entry in string_table)


register.snmp_section(
    name="snmp_extended_info",
    parse_function=parse_snmp_extended_info,
    host_label_function=get_device_type_label,
    fetch=SNMPTree(
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
    detect=exists(".1.3.6.1.2.1.47.1.1.1.1.*"),
)
