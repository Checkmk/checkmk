#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import asdict, dataclass

from cmk.agent_based.v2 import (
    Attributes,
    contains,
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)


@dataclass
class Section:
    model: str
    hardware_id: str
    serial: str
    version: str


def parse_infoblox_systeminfo(string_table: StringTable) -> Section | None:
    return Section(*string_table[0]) if string_table else None


snmp_section_infoblox_systeminfo = SimpleSNMPSection(
    name="infoblox_systeminfo",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7779.3.1.1.2.1",
        oids=[
            "4",  # IB-PLATFORMONE-MIB::ibHardwareType
            "5",  # IB-PLATFORMONE-MIB::ibHardwareId
            "6",  # IB-PLATFORMONE-MIB::ibSerialNumber
            "7",  # IB-PLATFORMONE-MIB::ibSerialVersion
        ],
    ),
    detect=contains(".1.3.6.1.2.1.1.1.0", "infoblox"),
    parse_function=parse_infoblox_systeminfo,
)


def inventory_infoblox_systeminfo(section: Section) -> InventoryResult:
    yield Attributes(path=["hardware", "system"], inventory_attributes=asdict(section))


inventory_plugin_infoblox_systeminfo = InventoryPlugin(
    name="infoblox_systeminfo",
    inventory_function=inventory_infoblox_systeminfo,
)
