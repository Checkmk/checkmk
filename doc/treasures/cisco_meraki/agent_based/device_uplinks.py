#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

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
