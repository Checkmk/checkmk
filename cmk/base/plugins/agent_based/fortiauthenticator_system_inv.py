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
from typing import Dict, List

Section = Dict[str, str]


def parse_fortiauthenticator_system_inv(string_table: List[StringTable]) -> Section:
    parsed = {
        'model': string_table[0][0][0],
        'serial': string_table[0][0][1],
    }
    return parsed


register.snmp_section(
    name='fortiauthenticator_system_inv',
    parse_function=parse_fortiauthenticator_system_inv,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.113.1',
            oids=[
                '1.0',  # facSysModel
                '2.0',  # facSysSerial
            ]),
    ],
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.8072.3.2.10'),
)


def inventory_fortiauthenticator_system_inv(section: Section) -> InventoryResult:
    model = section.get('model')
    serial = section.get('serial')
    yield Attributes(
        path=['hardware', 'Fortiauthenticator'],
        inventory_attributes={
            'Model': model,
            'Serial': serial,
        },
    )


register.inventory_plugin(
    name='fortiauthenticator_system_inv',
    inventory_function=inventory_fortiauthenticator_system_inv,
)
