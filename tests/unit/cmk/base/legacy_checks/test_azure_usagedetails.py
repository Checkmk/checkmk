#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.azure_usagedetails import (
    check_azure_usagedetails,
    discover_azure_usagedetails,
    parse_azure_usagedetails,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-0", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.05327698616264571, "CostUSD": 0.054594222263465136, "ResourceType": "Microsoft.Compute/disks", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-1", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.1, "CostUSD": 0.10247243, "ResourceType": "Microsoft.Compute/virtualMachines", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-2", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.06867924528301887, "CostUSD": 0.07, "ResourceType": "Microsoft.Network/publicIPAddresses", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
            ],
            [("Microsoft.Compute", {}), ("Microsoft.Network", {}), ("Summary", {})],
        ),
    ],
)
def test_discover_azure_usagedetails(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for azure_usagedetails check."""
    parsed = parse_azure_usagedetails(string_table)
    result = list(discover_azure_usagedetails(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Microsoft.Compute",
            {"levels": (0.1, 0.2)},
            [
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-0", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.05327698616264571, "CostUSD": 0.054594222263465136, "ResourceType": "Microsoft.Compute/disks", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-1", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.1, "CostUSD": 0.10247243, "ResourceType": "Microsoft.Compute/virtualMachines", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-2", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.06867924528301887, "CostUSD": 0.07, "ResourceType": "Microsoft.Network/publicIPAddresses", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
            ],
            [
                (
                    1,
                    "0.15 EUR (warn/crit at 0.10 EUR/0.20 EUR)",
                    [("service_costs_eur", 0.1532769861626457, 0.1, 0.2)],
                ),
                (0, "Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366"),
            ],
        ),
        (
            "Microsoft.Network",
            {},
            [
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-0", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.05327698616264571, "CostUSD": 0.054594222263465136, "ResourceType": "Microsoft.Compute/disks", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-1", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.1, "CostUSD": 0.10247243, "ResourceType": "Microsoft.Compute/virtualMachines", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-2", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.06867924528301887, "CostUSD": 0.07, "ResourceType": "Microsoft.Network/publicIPAddresses", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
            ],
            [
                (0, "0.07 EUR", [("service_costs_eur", 0.06867924528301887, None, None)]),
                (0, "Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366"),
            ],
        ),
        (
            "Summary",
            {},
            [
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-0", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.05327698616264571, "CostUSD": 0.054594222263465136, "ResourceType": "Microsoft.Compute/disks", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-1", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.1, "CostUSD": 0.10247243, "ResourceType": "Microsoft.Compute/virtualMachines", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
                ["Resource"],
                [
                    '{"id": "subscriptions/5698bf61-ff63-4299-94d2-5ed0f51e0366/providers/Microsoft.CostManagement/query/a2863eb3-b3f5-4356-8bb2-f8349a71fc1b", "name": "a2863eb3-b3f5-4356-8bb2-f8349a71fc1b-2", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": null, "properties": {"Cost": 0.06867924528301887, "CostUSD": 0.07, "ResourceType": "Microsoft.Network/publicIPAddresses", "ResourceGroupName": "checkmk-dev", "Tags": [], "Currency": "EUR"}, "group": "checkmk-dev", "subscription": "5698bf61-ff63-4299-94d2-5ed0f51e0366", "provider": "Microsoft.CostManagement"}'
                ],
            ],
            [
                (0, "0.22 EUR", [("service_costs_eur", 0.22195623144566456, None, None)]),
                (0, "Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366"),
            ],
        ),
    ],
)
def test_check_azure_usagedetails(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for azure_usagedetails check."""
    parsed = parse_azure_usagedetails(string_table)
    result = list(check_azure_usagedetails(item, params, parsed))
    assert result == expected_results
