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
    startswith,
)
from typing import Dict, List

Section = Dict[str, str]


def parse_fortigate_ha_inv(string_table: List[StringTable]) -> Section:
    system_modes = {
        1: 'standalone',
        2: 'activeActive',
        3: 'activePassive',
    }
    lbsched_modes = {
        1: 'none',
        2: 'hub',
        3: 'leastConnections',
        4: 'roundRobin',
        5: 'weightedRoundRobin',
        6: 'random',
        7: 'ipBased',
        8: 'ipPortBased',
    }
    parsed = {
        'mode': str(system_modes.get(int(string_table[0][0][0]))),
        'group_id': string_table[0][0][1],
        'prio': string_table[0][0][2],
        'sched': str(lbsched_modes.get(int(string_table[0][0][3]))),
        'group_name': string_table[0][0][4],
    }
    return parsed


register.snmp_section(
    name='fortigate_ha_inv',
    parse_function=parse_fortigate_ha_inv,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.101.13.1',
            oids=[
                '1',  # fgHaSystemMode
                '2',  # fgHaGroupId
                '3',  # fgHaPriority
                '6',  # fgHaSchedule
                '7',  # fgHaGroupName
            ]),
    ],
    detect=startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.101.1.'),
)


def inventory_fortigate_ha_inv(section: Section) -> InventoryResult:
    mode = section.get('mode')
    prio = section.get('prio')
    sched = section.get('sched')
    group_id = section.get('group_id')
    group_name = section.get('group_name')
    yield Attributes(
        path=['software', 'high_availability'],
        inventory_attributes={
            'Mode': mode,
            'Priority': prio,
            'Schedule': sched,
            'Group ID': group_id,
            'Group Name': group_name,
        },
    )


register.inventory_plugin(
    name='fortigate_ha_inv',
    inventory_function=inventory_fortigate_ha_inv,
)
