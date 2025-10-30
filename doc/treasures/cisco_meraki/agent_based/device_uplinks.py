#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-10-31
# File  : cdevice_uplinks.py (inventory plugin)

# inventory of cisco Meraki uplinks

# 2024-04-27: made data parsing more robust
# 2024-06-29: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_org_device_uplinks.py in to device_uplinks.py


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)

from cmk_addons.plugins.meraki.lib.utils import load_json

__uplinks = [
    {
        "addresses": [
            {
                "address": "192.168.20.3",
                "assignmentMode": "static",
                "gateway": "192.168.20.1",
                "protocol": "ipv4",
                "public": {
                    "address": "2.3.4.5"
                }
            }
        ],
        "interface": "man1"
    }
]


def parse_device_uplinks(string_table: StringTable) -> Sequence | None:
    return loaded_json[0]['uplinks'] if (loaded_json := load_json(string_table)) else None


agent_section_cisco_meraki_org_device_uplinks_info = AgentSection(
    name="cisco_meraki_org_device_uplinks_info",
    parse_function=parse_device_uplinks,
)


def inventory_device_uplinks(section: Sequence | None) -> InventoryResult:
    path = ['networking', 'uplinks']
    for uplink in section:
        if not (interface := uplink.get('interface')):
            continue
        for address in uplink.get('addresses', []):
            key_columns = {
                'interface': str(interface),
                **({"protocol": str(address['protocol'])} if address.get('protocol') is not None else {}),
                **({"address": str(address['address'])} if address.get('address') is not None else {}),
            }
            inventory_columns = {
                **({"assignment_mode": str(
                    address['assignmentMode']
                )} if address.get('assignmentMode') is not None else {}),
                **({"gateway": str(address['gateway'])} if address.get('gateway') is not None else {}),
                **({"public_address": str(address['public']['address'])} if address.get('public', {}).get(
                    'address') is not None else {}),
            }
            yield TableRow(
                path=path,
                key_columns=key_columns,
                inventory_columns=inventory_columns
            )


inventory_plugin_cisco_meraki_org_device_uplinks_info = InventoryPlugin(
    name="cisco_meraki_org_device_uplinks_info",
    inventory_function=inventory_device_uplinks,
)
