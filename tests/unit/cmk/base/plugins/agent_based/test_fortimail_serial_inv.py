#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from typing import Dict
from cmk.base.plugins.agent_based.fortimail_serial_inv import inventory_fortimail_serial_inv
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

Section: Dict[str, str] = {
    'model': 'FortiMail-VM',
    'serial': 'FEVM1234567890',
}

EXPECTED = [
    Attributes(
        path=['hardware', 'Fortimail'],
        inventory_attributes={
            'Model': 'FortiMail-VM',
            'Serial': 'FEVM1234567890',
        },
    ),
]


def test_fortimail_serial_inventory():
    yielded_inventory = list(inventory_fortimail_serial_inv(Section))
    assert yielded_inventory == EXPECTED
