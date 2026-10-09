#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.azure_v2.agent_based.azure_otel_resource import (
    agent_section_azure_otel_resource,
    inventory_plugin_azure_otel_resource,
)

from .inventory import get_inventory_value

AGENT_LINES = [
    ["Resource"],
    [
        '{"id": "/subscriptions/mysubid/resourceGroups/rg/providers/Microsoft.Network/publicIPAddresses/my-ip", "name": "my-ip", "type": "Microsoft.Network/publicIPAddresses", "location": "westeurope", "tags": {}, "tenant_id": "thetenantid", "tenant_name": "thetenant", "subscription_name": "mysubname", "subscription": "mysubid", "group": "rg"}'
    ],
]


def test_azure_otel_resource_inventory() -> None:
    parsed = agent_section_azure_otel_resource.parse_function(AGENT_LINES)
    inventory = inventory_plugin_azure_otel_resource.inventory_function(parsed)
    assert get_inventory_value(inventory, "tenant_name") == "thetenant"
