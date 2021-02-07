#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from cmk.base.plugins.agent_based.inventory_fortigate_ha import (
    parse_fortigate_ha,
    inventory_fortigate_ha,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

SECTION = {
    'mode': 'activePassive',
    'group_id': '11',
    'prio': '128',
    'sched': 'roundRobin',
    'group_name': 'SZAG-DE-SAR-FF',
}


def test_parse_fortigate_ha():
    assert parse_fortigate_ha([[
        '3',
        '11',
        '128',
        '4',
        'SZAG-DE-SAR-FF',
    ]]) == SECTION


def test_inventory_fortigate_ha():
    assert list(inventory_fortigate_ha(SECTION)) == [
        Attributes(
            path=['software', 'applications', 'fortinet', 'fortigate_high_availability'],
            inventory_attributes={
                'Mode': 'activePassive',
                'Priority': '128',
                'Schedule': 'roundRobin',
                'Group ID': '11',
                'Group Name': 'SZAG-DE-SAR-FF',
            },
        ),
    ]
