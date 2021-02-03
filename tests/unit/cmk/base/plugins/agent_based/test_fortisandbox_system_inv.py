#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from typing import List
from cmk.base.plugins.agent_based.fortisandbox_system_inv import inventory_fortisandbox_system_inv
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

Section: List[str] = ['v2.52-build0340 (GA)']

EXPECTED = [
    Attributes(
        path=['software', 'operating_system'],
        inventory_attributes={
            'version': 'v2.52-build0340 (GA)',
        },
    ),
]


def test_fortisandbox_system_inventory():
    yielded_inventory = list(inventory_fortisandbox_system_inv(Section))
    assert yielded_inventory == EXPECTED
