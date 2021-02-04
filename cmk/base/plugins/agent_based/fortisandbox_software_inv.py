#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from .agent_based_api.v1.type_defs import (
    InventoryResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    SNMPTree,
    equals,
    TableRow,
)
from typing import List

Section = List[List[str]]


def parse_fortisandbox_software_inv(string_table: List[StringTable]) -> Section:
    parsed = [["Tracer engine", string_table[0][0][0]], ["Rating engine", string_table[0][0][1]],
              ["System tools", string_table[0][0][2]], ["Sniffer", string_table[0][0][3]],
              ["Network alerts signature database", string_table[0][0][4]],
              ["Android analytic engine", string_table[0][0][5]],
              ["Android rating engine", string_table[0][0][6]]]
    return parsed


register.snmp_section(
    name="fortisandbox_software_inv",
    parse_function=parse_fortisandbox_software_inv,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.118.3.2',
            oids=[
                '1',  # fsaSysTracer
                '2',  # fsaSysRating
                '3',  # fsaSysTool
                '4',  # fsaSysSniffer
                '5',  # fsaSysIPS
                '6',  # fsaSysAndroidA
                '7',  # fsaSysAndroidR
            ]),
    ],
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.118.1.30006'),
)


def inventory_fortisandbox_software_inv(section: Section) -> InventoryResult:
    for sw in section:
        if sw[1] != "":
            yield TableRow(
                path=["software", "FortiSandbox"],
                key_columns={"Name": sw[0]},
                inventory_columns={
                    "Version": sw[1],
                },
            )


register.inventory_plugin(
    name='fortisandbox_software_inv',
    inventory_function=inventory_fortisandbox_software_inv,
)
