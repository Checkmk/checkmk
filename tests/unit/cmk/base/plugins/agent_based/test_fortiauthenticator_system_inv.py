#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from typing import Dict
from cmk.base.plugins.agent_based.fortiauthenticator_system_inv import inventory_fortiauthenticator_system_inv
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

Section: Dict[str, str] = {
    'model': 'FACVM',
    'serial': 'FAC-VMTM18000123',
}

EXPECTED = [
    Attributes(
        path=['hardware', 'Fortiauthenticator'],
        inventory_attributes={
            'Model': 'FACVM',
            'Serial': 'FAC-VMTM18000123',
        },
    ),
]


def test_fortiauthenticator_system_inventory():
    yielded_inventory = list(inventory_fortiauthenticator_system_inv(Section))
    assert yielded_inventory == EXPECTED
