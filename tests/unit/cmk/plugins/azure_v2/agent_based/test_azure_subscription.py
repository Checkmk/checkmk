#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from cmk.plugins.azure_v2.agent_based.azure_subscription import (
    agent_section_azure_subscription,
    inventory_plugin_azure_subscription,
)

from .inventory import get_inventory_value

AGENT_LINES = [
    ["Resource"],
    [
        '{"name": "mock_subscription_name", "tags": {}, "id": "mock_subscription_id", "type": "subscription", "group": "", "tenant_id": "c8d03e63-0d65-41a7-81fd-0ccc184bdd1a", "subscription_name": "mock_subscription_name"}'
    ],
]


def test_azure_subscription_inventory() -> None:
    parsed = agent_section_azure_subscription.parse_function(AGENT_LINES)
    inventory = inventory_plugin_azure_subscription.inventory_function(parsed)
    assert get_inventory_value(inventory, "Subscription name") == "mock_subscription_name"
