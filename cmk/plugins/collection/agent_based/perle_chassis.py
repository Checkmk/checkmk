#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.perle import DETECT_PERLE


@dataclass
class _Section:
    model: str
    serial: str
    bootloader: str
    firmware: str
    alarms: str
    diagnosis_state: str
    temp: float


def parse_perle_chassis(string_table: StringTable) -> _Section | None:
    if not string_table:
        return None
    model, serial, bootloader, firmware, alarms, diagnosis_state, temp_str = string_table[0]
    return _Section(
        model=model,
        serial=serial,
        bootloader=bootloader,
        firmware=firmware,
        alarms=alarms,
        diagnosis_state=diagnosis_state,
        temp=float(temp_str),
    )


snmp_section_perle_chassis = SimpleSNMPSection(
    name="perle_chassis",
    parse_function=parse_perle_chassis,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.1.1",
        oids=[
            "2",  # PERLE-MCR-MGT-MIB::chassisModelName
            "4",  # PERLE-MCR-MGT-MIB::chassisSerialNumber
            "5",  # PERLE-MCR-MGT-MIB::chassisBootloaderVersion
            "6",  # PERLE-MCR-MGT-MIB::chassisFirmwareVersion
            "7",  # PERLE-MCR-MGT-MIB::chassisOutStandWarnAlarms
            "8",  # PERLE-MCR-MGT-MIB::chassisDiagStatus
            "9",  # PERLE-MCR-MGT-MIB::chassisTemperature
        ],
    ),
    detect=DETECT_PERLE,
)


def inventory_perle_chassis(section: _Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "chassis"],
        inventory_attributes={
            "serial": section.serial,
            "model": section.model,
            "bootloader": section.bootloader,
            "firmware": section.firmware,
        },
    )


inventory_plugin_perle_chassis = InventoryPlugin(
    name="perle_chassis",
    inventory_function=inventory_perle_chassis,
)
