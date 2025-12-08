#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com


# sample snmpwalk
# .1.3.6.1.2.1.31.1.1.1.1.1 = STRING: lo
# .1.3.6.1.2.1.31.1.1.1.1.2 = STRING: eth-idrc0
# .1.3.6.1.2.1.31.1.1.1.1.3 = STRING: eth1
# .1.3.6.1.2.1.31.1.1.1.1.4 = STRING: eth2
# .1.3.6.1.2.1.31.1.1.1.1.5 = STRING: eth3
# .1.3.6.1.2.1.31.1.1.1.1.6 = STRING: Mgmt
# .1.3.6.1.2.1.31.1.1.1.1.7 = STRING: bond1
# .1.3.6.1.2.1.31.1.1.1.1.8 = STRING: bond1.3000
# .1.3.6.1.2.1.31.1.1.1.1.9 = STRING: bond1.3001
#


from pydantic import BaseModel

from cmk.agent_based.v2 import (
    exists,
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)


class IfNameEntry(BaseModel):
    index: int
    name: str


def parse_if_name(string_table: StringTable) -> list[IfNameEntry]:
    return [
        IfNameEntry(index=int(if_index), name=if_name)
        for if_index, if_name in string_table
        if if_name and if_index.isdigit()
    ]


def inventory_if_name(section: list[IfNameEntry]) -> InventoryResult:
    path = ["networking", "interfaces"]
    for entry in section:
        yield TableRow(
            path=path,
            key_columns={"index": entry.index},
            inventory_columns={"name": entry.name},
        )


snmp_section_inv_if_name = SimpleSNMPSection(
    name="inv_if_name",
    parse_function=parse_if_name,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.31.1.1.1",  # IF-MIB::ifXTable
        oids=[
            OIDEnd(),  # ifIndex
            "1",  # ifName
        ],
    ),
    detect=exists(".1.3.6.1.2.1.31.1.1.1.1.*"),
)

inventory_plugin_if_name = InventoryPlugin(
    name="inv_if_name",
    inventory_function=inventory_if_name,
)
