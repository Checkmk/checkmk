#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# APC NetShelter Advanced Rack PDU (APDU series) - HW/SW inventory
# MIB reference: mibs/APC-CPDU-v1_9-MIB.txt
#
# .1.3.6.1.4.1.318.1.1.32.1.2.1.10  "346-415V, 63A"  - electrical rating
# .1.3.6.1.4.1.318.1.1.32.1.2.1.11  "APDU10450SM"    - model
# .1.3.6.1.4.1.318.1.1.32.1.2.1.12  "XX0000Y00000"   - serial number
# .1.3.6.1.4.1.318.1.1.32.1.2.1.13  "2024/01/15"     - manufacture date
# .1.3.6.1.4.1.318.1.1.32.1.2.1.14  "3.0.0"          - firmware version
# .1.3.6.1.2.1.1.5                   "mypdu"          - sysName
# .1.3.6.1.2.1.1.6                   ""               - sysLocation

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
from cmk.plugins.collection.agent_based.apc_netshelterpdu_power import (
    DETECT_APC_NETSHELTERPDU,
)


@dataclass(frozen=True, kw_only=True)
class APCNetShelterPDUInventory:
    model: str
    serial_number: str
    firmware_version: str
    manufacture_date: str
    electrical_rating: str
    system_name: str
    location: str


def parse_apc_netshelterpdu_inventory(
    string_table: Sequence[StringTable],
) -> APCNetShelterPDUInventory | None:
    if not string_table or not string_table[0]:
        return None

    device_info = string_table[0][0]
    sys_info = string_table[1][0] if len(string_table) > 1 and string_table[1] else ["", ""]

    return APCNetShelterPDUInventory(
        electrical_rating=device_info[0],
        model=device_info[1],
        serial_number=device_info[2],
        manufacture_date=device_info[3],
        firmware_version=device_info[4],
        system_name=sys_info[0],
        location=sys_info[1],
    )


snmp_section_apc_netshelterpdu_inventory = SNMPSection(
    name="apc_netshelterpdu_inventory",
    parse_function=parse_apc_netshelterpdu_inventory,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.32.1.2.1",
            oids=[
                "10",  # electrical rating
                "11",  # model
                "12",  # serial number
                "13",  # manufacture date
                "14",  # firmware version
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=[
                "5",  # sysName
                "6",  # sysLocation
            ],
        ),
    ],
    detect=DETECT_APC_NETSHELTERPDU,
)


def inventorize_apc_netshelterpdu(section: APCNetShelterPDUInventory) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "manufacturer": "APC",
            "model": section.model,
            "serial": section.serial_number,
            "manufacture_date": section.manufacture_date,
            "electrical_rating": section.electrical_rating,
        },
    )

    yield Attributes(
        path=["software", "firmware"],
        inventory_attributes={
            "vendor": "APC",
            "version": section.firmware_version,
        },
    )

    networking_attrs: dict[str, str] = {}
    if section.system_name:
        networking_attrs["hostname"] = section.system_name
    if section.location:
        networking_attrs["location"] = section.location
    if networking_attrs:
        yield Attributes(path=["networking"], inventory_attributes=networking_attrs)


inventory_plugin_apc_netshelterpdu_inventory = InventoryPlugin(
    name="apc_netshelterpdu_inventory",
    inventory_function=inventorize_apc_netshelterpdu,
)
