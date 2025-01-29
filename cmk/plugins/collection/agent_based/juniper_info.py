#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)


class Section(NamedTuple):
    serial: str
    model: str


def parse_juniper_info(string_table: StringTable) -> Section | None:
    for model, serial in string_table:
        return Section(serial=serial, model=model)
    return None


snmp_section_juniper_info = SimpleSNMPSection(
    name="juniper_info",
    parse_function=parse_juniper_info,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1",
        oids=[
            "2",  # jnxBoxDescr
            "3",  # jnxBoxSerialNo
        ],
    ),
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636.1.1.1.2"),
)


def inventory_juniper_info(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "serial_number": section.serial,
            "model_name": section.model,
        },
    )


inventory_plugin_juniper_info = InventoryPlugin(
    name="juniper_info",
    inventory_function=inventory_juniper_info,
)
