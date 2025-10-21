#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from cmk.plugins.azure_v2.agent_based.azure_resourcegroups import (
    agent_section_azure_resourcegroups,
    inventory_plugin_azure_resourcegroups,
)

from .inventory import get_inventory_value

AGENT_LINES = [
    ["Resource"],
    [
        '{"id": "/subscriptions/mysubid/resourceGroups/TheCoolRG", "name": "thecoolrg", "type": "Microsoft.Resources/resourceGroups", "location": "germanywestcentral", "properties": {"provisioningState": "Succeeded"}, "tags": {}, "tenant_id": "thetenantid", "subscription_name": "Subscription-Name_here-Yipeee", "subscription": "mysubid", "group": "thecoolrg"}'
    ],
]


def test_azure_resourcegroups_inventory() -> None:
    parsed = agent_section_azure_resourcegroups.parse_function(AGENT_LINES)
    inventory = inventory_plugin_azure_resourcegroups.inventory_function(parsed)
    assert get_inventory_value(inventory, "Subscription name") == "Subscription-Name_here-Yipeee"
