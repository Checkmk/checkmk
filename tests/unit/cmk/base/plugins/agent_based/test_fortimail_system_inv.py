#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from typing import List
from cmk.base.plugins.agent_based.fortimail_system_inv import inventory_fortimail_system_inv
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

Section: List[str] = ['v5.4,build719,180328 (5.4.5 GA)']

EXPECTED = [
    Attributes(
        path=['software', 'operating_system'],
        inventory_attributes={
            'version': 'v5.4,build719,180328 (5.4.5 GA)',
        },
    ),
]


def test_fortimail_system_inventory():
    yielded_inventory = list(inventory_fortimail_system_inv(Section))
    assert yielded_inventory == EXPECTED
