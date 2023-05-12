#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "azure_usagedetails"

info = [
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

discovery = {
    "": [
        ("Microsoft.Compute", {}),
        ("Microsoft.Network", {}),
        ("Summary", {}),
    ],
}

checks = {
    "": [
        (
            "Microsoft.Compute",
            {"levels": (0.1, 0.2)},
            [
                (
                    1,
                    "0.15 EUR (warn/crit at 0.10 EUR/0.20 EUR)",
                    [
                        ("service_costs_eur", 0.1532769861626457, 0.1, 0.2),
                    ],
                ),
                (0, "Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366", []),
            ],
        ),
        (
            "Microsoft.Network",
            {},
            [
                (
                    0,
                    "0.07 EUR",
                    [
                        ("service_costs_eur", 0.06867924528301887),
                    ],
                ),
                (0, "Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366", []),
            ],
        ),
        (
            "Summary",
            {},
            [
                (
                    0,
                    "0.22 EUR",
                    [
                        ("service_costs_eur", 0.22195623144566456),
                    ],
                ),
                (0, "Subscription: 5698bf61-ff63-4299-94d2-5ed0f51e0366", []),
            ],
        ),
    ],
}
