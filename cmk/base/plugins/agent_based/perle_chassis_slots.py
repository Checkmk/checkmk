#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.2.1.1 1 --> PERLE-MCR-MGT-MIB::mcrChassisSlotIndex.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.2.1.2 2 --> PERLE-MCR-MGT-MIB::mcrChassisSlotIndex.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.3.1.1 PerleMC01 --> PERLE-MCR-MGT-MIB::mcrUserDefinedModuleName.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.3.1.2 CM-1000-SFP --> PERLE-MCR-MGT-MIB::mcrUserDefinedModuleName.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.4.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.4.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.6.1.1 101-693515M10019 --> PERLE-MCR-MGT-MIB::mcrModuleSerialNumber.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.6.1.2 102-094710M10033 --> PERLE-MCR-MGT-MIB::mcrModuleSerialNumber.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.7.1.1 01.01.0004 --> PERLE-MCR-MGT-MIB::mcrModuleBootloaderVersion.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.7.1.2 1.1 --> PERLE-MCR-MGT-MIB::mcrModuleBootloaderVersion.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.8.1.1 1.8.G4 --> PERLE-MCR-MGT-MIB::mcrModuleFirmwareVersion.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.8.1.2 1.2G1 --> PERLE-MCR-MGT-MIB::mcrModuleFirmwareVersion.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.9.1.1 0 --> PERLE-MCR-MGT-MIB::mcrModuleoOutStandWarnAlarms.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.9.1.2 0 --> PERLE-MCR-MGT-MIB::mcrModuleoOutStandWarnAlarms.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.10.1.1 0 --> PERLE-MCR-MGT-MIB::mcrModuleDiagStatus.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.10.1.2 0 --> PERLE-MCR-MGT-MIB::mcrModuleDiagStatus.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.11.1.1 -2 --> PERLE-MCR-MGT-MIB::mcrModuleTypeInserted.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.11.1.2 1 --> PERLE-MCR-MGT-MIB::mcrModuleTypeInserted.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.19.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.3.1.19.1.2

from .agent_based_api.v1 import register, SNMPTree, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.perle import DETECT_PERLE

Section = StringTable

register.snmp_section(
    name="perle_chassis_slots",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.3.1",
        oids=[
            "2",  # PERLE-MCR-MGT-MIB::mcrChassisSlotIndex
            "3",  # PERLE-MCR-MGT-MIB::mcrDefinedModuleName
            "4",  # PERLE-MCR-MGT-MIB::mcrModuleModelName
            "6",  # PERLE-MCR-MGT-MIB::mcrModuleSerialNumber
            "7",  # PERLE-MCR-MGT-MIB::mcrModuleBootloaderVersion
            "8",  # PERLE-MCR-MGT-MIB::mcrModuleFirmwareVersion
            "9",  # PERLE-MCR-MGT-MIB::mcrModuleoOutStandWarnAlarms
            "10",  # PERLE-MCR-MGT-MIB::mcrModuleDiagStatus
            "11",  # PERLE-MCR-MGT-MIB::mcrModuleTypeInserted
            "19",  # PERLE-MCR-MGT-MIB::mcrModuleModelDesc
        ],
    ),
    detect=DETECT_PERLE,
)


_MAP_TYPES = {
    "-3": "unManaged",
    "-2": "mcrMgt",
    "-1": "unknown",
    "0": "empty",
    "1": "cm1000Fixed",
    "2": "cm100Fixed",
    "3": "cm1110RateConv",
    "4": "cm110RateConv",
    "5": "cm100mmFixed",
    "6": "cm1000mmFixed",
    "7": "cm10gFixed",
    "8": "exCM",
    "9": "cm10gt",
    "10": "cm4gpt",
}


def inventory_perle_chassis_slots(section: Section) -> InventoryResult:
    for index, name, modelname, serial, bootloader, fw, _alarms, _diagstate, ty, descr in section:
        if ty != "0":
            yield TableRow(
                path=["hardware", "components", "modules"],
                key_columns={
                    "index": index,
                    "name": name,
                },
                inventory_columns={
                    "description": descr,
                    "model": modelname,
                    "serial": serial,
                    "bootloader": bootloader,
                    "firmware": fw,
                    "type": _MAP_TYPES[ty],
                },
                status_columns={},
            )


register.inventory_plugin(
    name="perle_chassis_slots",
    inventory_function=inventory_perle_chassis_slots,
)
