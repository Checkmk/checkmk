#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType

from cmk.agent_based.v2 import (
    Attributes,
    contains,
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

_Serial = NewType("_Serial", str)


def parse_hp_proliant_systeminfo(string_table: StringTable) -> _Serial | None:
    return _Serial(string_table[0][0]) if string_table else None


snmp_section_hp_proliant_systeminfo = SimpleSNMPSection(
    name="hp_proliant_systeminfo",
    parse_function=parse_hp_proliant_systeminfo,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.2.2.2",
        oids=["1"],
    ),
    detect=contains(".1.3.6.1.4.1.232.2.2.4.2.0", "proliant"),
)


def inventory_hp_proliant_systeminfo(section: _Serial) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "serial": section,
        },
    )


inventory_plugin_hp_proliant_systeminfo = InventoryPlugin(
    name="hp_proliant_systeminfo",
    inventory_function=inventory_hp_proliant_systeminfo,
)
