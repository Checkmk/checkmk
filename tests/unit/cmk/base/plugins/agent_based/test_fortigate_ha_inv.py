#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from typing import Dict
from cmk.base.plugins.agent_based.fortigate_ha_inv import inventory_fortigate_ha_inv
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

Section: Dict[str, str] = {
    'mode': 'activePassive',
    'group_id': '11',
    'prio': '128',
    'sched': 'roundRobin',
    'group_name': 'SZAG-DE-SAR-FF',
}

EXPECTED = [
    Attributes(
        path=['software', 'high_availability'],
        inventory_attributes={
            'Mode': 'activePassive',
            'Priority': '128',
            'Schedule': 'roundRobin',
            'Group ID': '11',
            'Group Name': 'SZAG-DE-SAR-FF',
        },
    ),
]


def test_fortigate_ha_inventory():
    yielded_inventory = list(inventory_fortigate_ha_inv(Section))
    assert yielded_inventory == EXPECTED
