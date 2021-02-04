#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from typing import List
from cmk.base.plugins.agent_based.fortisandbox_software_inv import inventory_fortisandbox_software_inv
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow

Section: List[List[str]] = [['Tracer engine', '5.2.50534'], ['Rating engine', '2.4.20034'],
                            ['System tools', '3.2.279'], ['Sniffer', '4.478'],
                            ['Network alerts signature database', '14.613'],
                            ['Android analytic engine', ''], ['Android rating engine', '']]

EXPECTED = [
    TableRow(
        path=['software', 'FortiSandbox'],
        key_columns={'Name': 'Tracer engine'},
        inventory_columns={
            'Version': '5.2.50534',
        },
    ),
    TableRow(
        path=['software', 'FortiSandbox'],
        key_columns={'Name': 'Rating engine'},
        inventory_columns={
            'Version': '2.4.20034',
        },
    ),
    TableRow(
        path=['software', 'FortiSandbox'],
        key_columns={'Name': 'System tools'},
        inventory_columns={
            'Version': '3.2.279',
        },
    ),
    TableRow(
        path=['software', 'FortiSandbox'],
        key_columns={'Name': 'Sniffer'},
        inventory_columns={
            'Version': '4.478',
        },
    ),
    TableRow(
        path=['software', 'FortiSandbox'],
        key_columns={'Name': 'Network alerts signature database'},
        inventory_columns={
            'Version': '14.613',
        },
    ),
]


def test_fortisandbox_software_inventory():
    yielded_inventory = list(inventory_fortisandbox_software_inv(Section))
    assert yielded_inventory == EXPECTED
