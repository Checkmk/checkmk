#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from .agent_based_api.v1.type_defs import (
    InventoryResult,
    StringTable,
)
from .agent_based_api.v1 import (
    Attributes,
    register,
    SNMPTree,
    equals,
)
from typing import List

Section = List[str]


def parse_fortimail_system_inv(string_table: List[StringTable]) -> Section:
    return string_table[0][0]


register.snmp_section(
    name="fortimail_system_inv",
    parse_function=parse_fortimail_system_inv,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.105.1',
            oids=[
                '3',  # fmlSysVersion
            ]),
    ],
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.105'),
)


def inventory_fortimail_system_inv(section: Section) -> InventoryResult:
    fw_version = section[0]
    yield Attributes(
        path=["software", "operating_system"],
        inventory_attributes={
            "version": fw_version,
        },
    )


register.inventory_plugin(
    name='fortimail_system_inv',
    inventory_function=inventory_fortimail_system_inv,
)
