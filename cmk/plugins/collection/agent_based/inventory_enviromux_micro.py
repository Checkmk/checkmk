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
from cmk.plugins.lib.enviromux import DETECT_ENVIROMUX_MICRO


@dataclass
class EnviromuxMicroInformation:
    unit_name: str
    device_model: str
    serial_number: str
    firmware_revision: str


def parse_enviromux_micro_information(
    string_table: StringTable,
) -> EnviromuxMicroInformation | None:
    """
    >>> parse_enviromux_micro_information([["test-name", "E-MICRO-T", "799", "3.20"]])
    EnviromuxMicroInformation(unit_name='test-name', device_model='E-MICRO-T', serial_number='799', firmware_revision='3.20')
    """
    return (
        EnviromuxMicroInformation(
            unit_name=string_table[0][0],
            device_model=string_table[0][1],
            serial_number=string_table[0][2],
            firmware_revision=string_table[0][3],
        )
        if string_table
        else None
    )


snmp_section_enviromux_micro_information = SimpleSNMPSection(
    name="enviromux_micro_information",
    parse_function=parse_enviromux_micro_information,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3699.1.1.12.1.100",
        oids=[
            "1",  # unitName
            "2",  # deviceModel
            "3",  # serialNumber
            "4",  # firmwareRevision
        ],
    ),
    detect=DETECT_ENVIROMUX_MICRO,
)


def inventory_enviromux_micro_information(
    section: EnviromuxMicroInformation | None,
) -> InventoryResult:
    if not section:
        return

    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "Description": section.unit_name,
            "Model": section.device_model,
            "Serial Number": section.serial_number,
        },
    )
    yield Attributes(
        path=["software", "firmware"],
        inventory_attributes={
            "Vendor": "NTI",
            "Version": section.firmware_revision,
        },
    )


inventory_plugin_enviromux_micro_information = InventoryPlugin(
    name="enviromux_micro_information",
    inventory_function=inventory_enviromux_micro_information,
)
