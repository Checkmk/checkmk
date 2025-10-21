#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.azure_usagedetails import (
    check_azure_usagedetails,
    discover_azure_usagedetails,
    parse_azure_usagedetails,
)

STRING_TABLE = [
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
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            STRING_TABLE,
            [
                Service(item="Microsoft.Compute"),
                Service(item="Microsoft.Network"),
                Service(item="Summary"),
            ],
        ),
    ],
)
def test_discover_azure_usagedetails(
    string_table: StringTable, expected_discoveries: DiscoveryResult
) -> None:
    parsed = parse_azure_usagedetails(string_table)
    result = list(discover_azure_usagedetails(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Microsoft.Compute",
            {"costs": ("fixed", (0.1, 0.2))},
            STRING_TABLE,
            [
                Result(
                    state=State.WARN,
                    summary="0.15 EUR (warn/crit at 0.10 EUR/0.20 EUR)",
                ),
                Metric(name="service_costs_eur", value=0.1532769861626457, levels=(0.1, 0.2)),
                Result(
                    state=State.OK, summary="Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366"
                ),
            ],
        ),
        (
            "Microsoft.Network",
            {},
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="0.07 EUR",
                ),
                Metric(name="service_costs_eur", value=0.06867924528301887, levels=(None, None)),
                Result(
                    state=State.OK, summary="Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366"
                ),
            ],
        ),
        (
            "Summary",
            {},
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="0.22 EUR",
                ),
                Metric(name="service_costs_eur", value=0.22195623144566456, levels=(None, None)),
                Result(
                    state=State.OK, summary="Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366"
                ),
            ],
        ),
    ],
)
def test_check_azure_usagedetails(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: CheckResult
) -> None:
    parsed = parse_azure_usagedetails(string_table)
    result = list(check_azure_usagedetails(item, params, parsed))
    assert result == expected_results
