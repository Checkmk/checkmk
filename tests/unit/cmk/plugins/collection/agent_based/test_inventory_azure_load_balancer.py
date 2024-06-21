#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import InventoryResult, TableRow
from cmk.plugins.azure.agent_based.azure_load_balancer import parse_load_balancer
from cmk.plugins.collection.agent_based.inventory_azure_load_balancer import inventory_load_balancer
from cmk.plugins.lib.azure_load_balancer import Section

SECTION = parse_load_balancer(
    [
        ["Resource"],
        [
            '{"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001", "name": "az-lbe-001", "type": "Microsoft.Network/loadBalancers", "location": "fijieast", "subscription": "f00", "group": "az-rg-lbe-001", "provider": "Microsoft.Network", "properties": {"frontend_ip_configs": {"/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001": {"name": "az-frontend-ip-lb-001", "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001", "privateIPAllocationMethod": "Dynamic", "public_ip_address": {"dns_fqdn": "", "name": "10.1.1.1", "location": "eastus", "ipAddress": "20.199.181.70", "publicIPAllocationMethod": "Static"}}}, "inbound_nat_rules": [{"name": "az-lbe-nat-in-rule-001", "frontendIPConfiguration": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"}, "frontendPort": 6556, "backendPort": 6556, "backend_ip_config": {"name": "vm837-nic-conf", "privateIPAddress": "10.10.10.236", "privateIPAllocationMethod": "Static"}}, {"name": "az-lbe-nat-in-rule-002", "frontendIPConfiguration": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"}, "frontendPort": 6557, "backendPort": 6557, "backend_ip_config": {"name": "vm838-nic-conf", "privateIPAddress": "10.10.10.237", "privateIPAllocationMethod": "Static"}}], "backend_pools": {"/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01": {"name": "az-lbe-001-backendpool01", "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01", "addresses": [{"name": "nic-config-346", "privateIPAddress": "10.27.145.4", "privateIPAllocationMethod": "Static", "primary": true}, {"name": "az-vm-184-nic-config", "privateIPAddress": "10.27.144.40", "privateIPAllocationMethod": "Static", "primary": true}]}}, "outbound_rules": [{"name": "az-out-all-001", "protocol": "All", "idleTimeoutInMinutes": 4, "backendAddressPool": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01"}}]}}'
        ],
        ["metrics following", "5"],
        [
            '{"name": "ByteCount", "aggregation": "total", "value": 15000.0, "unit": "bytes", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter": null}'
        ],
        [
            '{"name": "AllocatedSnatPorts", "aggregation": "average", "value": 15.5, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'
        ],
        [
            '{"name": "UsedSnatPorts", "aggregation": "average", "value": 2.8, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'
        ],
        [
            '{"name": "VipAvailability", "aggregation": "average", "value": 100.0, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'
        ],
        [
            '{"name": "DipAvailability", "aggregation": "average", "value": 50.0, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'
        ],
    ],
)


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            SECTION,
            [
                TableRow(
                    path=["software", "applications", "azure", "load_balancers"],
                    key_columns={"name": "az-lbe-001"},
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "inbound_nat_rules",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "inbound_nat_rule": "az-lbe-nat-in-rule-001",
                    },
                    inventory_columns={"frontend_port": 6556, "backend_port": 6556},
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "inbound_nat_rules",
                        "public_ips",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "inbound_nat_rule": "az-lbe-nat-in-rule-001",
                        "public_ip_name": "10.1.1.1",
                    },
                    inventory_columns={
                        "location": "eastus",
                        "ip_address": "20.199.181.70",
                        "ip_allocation_method": "Static",
                        "dns_fqdn": "",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "inbound_nat_rules",
                        "backend_ip_configs",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "inbound_nat_rule": "az-lbe-nat-in-rule-001",
                        "backend_ip_config": "vm837-nic-conf",
                    },
                    inventory_columns={
                        "ip_address": "10.10.10.236",
                        "ip_allocation_method": "Static",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "inbound_nat_rules",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "inbound_nat_rule": "az-lbe-nat-in-rule-002",
                    },
                    inventory_columns={"frontend_port": 6557, "backend_port": 6557},
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "inbound_nat_rules",
                        "public_ips",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "inbound_nat_rule": "az-lbe-nat-in-rule-002",
                        "public_ip_name": "10.1.1.1",
                    },
                    inventory_columns={
                        "location": "eastus",
                        "ip_address": "20.199.181.70",
                        "ip_allocation_method": "Static",
                        "dns_fqdn": "",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "inbound_nat_rules",
                        "backend_ip_configs",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "inbound_nat_rule": "az-lbe-nat-in-rule-002",
                        "backend_ip_config": "vm838-nic-conf",
                    },
                    inventory_columns={
                        "ip_address": "10.10.10.237",
                        "ip_allocation_method": "Static",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "azure", "load_balancers", "outbound_rules"],
                    key_columns={"load_balancer": "az-lbe-001", "outbound_rule": "az-out-all-001"},
                    inventory_columns={"protocol": "All", "idle_timeout": 4},
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "outbound_rules",
                        "backend_pools",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "outbound_rule": "az-out-all-001",
                        "backend_pool": "az-lbe-001-backendpool01",
                    },
                    inventory_columns={},
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "outbound_rules",
                        "backend_pools",
                        "addresses",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "outbound_rule": "az-out-all-001",
                        "backend_pool": "az-lbe-001-backendpool01",
                        "address_name": "nic-config-346",
                    },
                    inventory_columns={
                        "ip_address": "10.27.145.4",
                        "ip_allocation_method": "Static",
                        "primary": True,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=[
                        "software",
                        "applications",
                        "azure",
                        "load_balancers",
                        "outbound_rules",
                        "backend_pools",
                        "addresses",
                    ],
                    key_columns={
                        "load_balancer": "az-lbe-001",
                        "outbound_rule": "az-out-all-001",
                        "backend_pool": "az-lbe-001-backendpool01",
                        "address_name": "az-vm-184-nic-config",
                    },
                    inventory_columns={
                        "ip_address": "10.27.144.40",
                        "ip_allocation_method": "Static",
                        "primary": True,
                    },
                    status_columns={},
                ),
            ],
        )
    ],
)
def test_inventory_load_balancer(section: Section, expected_result: InventoryResult) -> None:
    assert list(inventory_load_balancer(section)) == expected_result
