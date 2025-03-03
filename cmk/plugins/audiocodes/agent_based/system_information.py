#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
    SNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_AUDIOCODES, parse_license_key_list


@dataclass(frozen=True, kw_only=True)
class System:
    product: str
    name: str
    serial_number: str
    type: str
    software_version: str
    license_key_list: str
    call_progress_tones: str


def parse_audiocodes_system_information(string_table: Sequence[StringTable]) -> System | None:
    if not string_table[0] or not string_table[1]:
        return None

    return System(
        product=string_table[0][0][0].replace("Product: ", ""),
        name=string_table[1][0][0],
        serial_number=string_table[1][0][1],
        type=string_table[1][0][2],
        software_version=string_table[1][0][3],
        license_key_list=parse_license_key_list(string_table[1][0][4]),
        call_progress_tones=string_table[1][0][5],
    )


snmp_section_audiocodes_system_information = SNMPSection(
    name="audiocodes_system_information",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1.1",
            oids=["0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10",
            oids=[
                "2.3.1.0",  # acSysIdName
                "2.3.2.0",  # acSysIdSerialNumber
                "2.1.1.0",  # acSysTypeProduct
                "2.2.1.0",  # acSysVersionSoftware
                "1.5.2.0",  # acSysLicenseKeyActiveList
                "1.6.1.0",  # acSysFileCpt
            ],
        ),
    ],
    parse_function=parse_audiocodes_system_information,
)


def inventory_audiocodes_system_information(section: System) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "product": section.product,
            "model": section.name,
            "type": section.type,
            "serial": section.serial_number,
            "software_version": section.software_version,
            "license_key_list": section.license_key_list,
        },
    )

    yield Attributes(
        path=["hardware", "uploaded_files"],
        inventory_attributes={"call_progress_tones": section.call_progress_tones},
    )


inventory_plugin_audiocodes_system_information = InventoryPlugin(
    name="audiocodes_system_information",
    inventory_function=inventory_audiocodes_system_information,
)
