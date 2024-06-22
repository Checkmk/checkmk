#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    Attributes,
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIAUTHENTICATOR

Section = Mapping[str, str]


def parse_fortiauthenticator_system(string_table: StringTable) -> Section | None:
    """
    >>> parse_fortiauthenticator_system([['FACVM', 'FAC-VMTM18000123']])
    {'model': 'FACVM', 'serial': 'FAC-VMTM18000123'}
    """
    return (
        {
            "model": string_table[0][0],
            "serial": string_table[0][1],
        }
        if string_table
        else None
    )


snmp_section_fortiauthenticator_system = SimpleSNMPSection(
    name="fortiauthenticator_system",
    parse_function=parse_fortiauthenticator_system,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.113.1",
        oids=[
            "1",  # facSysModel
            "2",  # facSysSerial
        ],
    ),
    detect=DETECT_FORTIAUTHENTICATOR,
)


def inventory_fortiauthenticator_system(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "Model": section["model"],
            "Serial number": section["serial"],
        },
    )


inventory_plugin_fortiauthenticator_system = InventoryPlugin(
    name="fortiauthenticator_system",
    inventory_function=inventory_fortiauthenticator_system,
)
