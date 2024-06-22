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
from cmk.plugins.lib.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, str]


def parse_fortimail_system(string_table: StringTable) -> Section | None:
    """
    >>> parse_fortimail_system([["model 1a", "12345", "v5.4,build719,180328 (5.4.5 GA)"]])
    {'model': 'model 1a', 'serial': '12345', 'os': 'v5.4,build719,180328 (5.4.5 GA)'}
    """
    return (
        dict(
            zip(
                [
                    "model",
                    "serial",
                    "os",
                ],
                string_table[0],
            )
        )
        if string_table
        else None
    )


snmp_section_fortimail_system = SimpleSNMPSection(
    name="fortimail_system",
    parse_function=parse_fortimail_system,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1",
        oids=[
            "1",  # fmlSysModel
            "2",  # fmlSysSerial
            "3",  # fmlSysVersion
        ],
    ),
    detect=DETECT_FORTIMAIL,
)


def inventory_fortimail_system(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "model": section["model"],
            "serial": section["serial"],
        },
    )
    yield Attributes(
        path=["software", "operating_system"],
        inventory_attributes={
            "version": section["os"],
        },
    )


inventory_plugin_fortimail_system = InventoryPlugin(
    name="fortimail_system",
    inventory_function=inventory_fortimail_system,
)
