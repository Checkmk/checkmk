#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, State, StringTable
from cmk.plugins.azure.agent_based.azure_load_balancer import (
    check_byte_count,
    check_health,
    check_snat,
    parse_load_balancer,
)
from cmk.plugins.lib.azure import AzureMetric, FrontendIpConfiguration, PublicIP, Resource
from cmk.plugins.lib.azure_load_balancer import (
    BackendIpConfiguration,
    InboundNatRule,
    LoadBalancer,
    LoadBalancerBackendAddress,
    LoadBalancerBackendPool,
    OutboundRule,
    Section,
)

SECTION = {
    "az-lbe-001": LoadBalancer(
        resource=Resource(
            id="/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001",
            name="az-lbe-001",
            type="Microsoft.Network/loadBalancers",
            group="az-rg-lbe-001",
            kind=None,
            location="fijieast",
            tags={},
            properties={
                "frontend_ip_configs": {
                    "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001": {
                        "name": "az-frontend-ip-lb-001",
                        "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001",
                        "privateIPAllocationMethod": "Dynamic",
                        "public_ip_address": {
                            "dns_fqdn": "",
                            "name": "10.1.1.1",
                            "location": "eastus",
                            "ipAddress": "20.199.181.70",
                            "publicIPAllocationMethod": "Static",
                        },
                    }
                },
                "inbound_nat_rules": [
                    {
                        "name": "az-lbe-nat-in-rule-001",
                        "frontendIPConfiguration": {
                            "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"
                        },
                        "frontendPort": 6556,
                        "backendPort": 6556,
                        "backend_ip_config": {
                            "name": "vm837-nic-conf",
                            "privateIPAddress": "10.10.10.236",
                            "privateIPAllocationMethod": "Static",
                        },
                    },
                    {
                        "name": "az-lbe-nat-in-rule-002",
                        "frontendIPConfiguration": {
                            "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"
                        },
                        "frontendPort": 6557,
                        "backendPort": 6557,
                        "backend_ip_config": {
                            "name": "vm838-nic-conf",
                            "privateIPAddress": "10.10.10.237",
                            "privateIPAllocationMethod": "Static",
                        },
                    },
                ],
                "backend_pools": {
                    "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01": {
                        "name": "az-lbe-001-backendpool01",
                        "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01",
                        "addresses": [
                            {
                                "name": "nic-config-346",
                                "privateIPAddress": "10.27.145.4",
                                "privateIPAllocationMethod": "Static",
                                "primary": True,
                            },
                            {
                                "name": "az-vm-184-nic-config",
                                "privateIPAddress": "10.27.144.40",
                                "privateIPAllocationMethod": "Static",
                                "primary": True,
                            },
                        ],
                    }
                },
                "outbound_rules": [
                    {
                        "name": "az-out-all-001",
                        "protocol": "All",
                        "idleTimeoutInMinutes": 4,
                        "backendAddressPool": {
                            "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01"
                        },
                    },
                    {
                        "name": "az-out-all-002",
                        "protocol": "All",
                        "idleTimeoutInMinutes": 4,
                        "backendAddressPool": {
                            "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool02"
                        },
                    },
                ],
            },
            specific_info={},
            metrics={
                "total_ByteCount": AzureMetric(
                    name="ByteCount", aggregation="total", value=15000.0, unit="bytes"
                ),
                "average_AllocatedSnatPorts": AzureMetric(
                    name="AllocatedSnatPorts", aggregation="average", value=15.5, unit="count"
                ),
                "average_UsedSnatPorts": AzureMetric(
                    name="UsedSnatPorts", aggregation="average", value=2.8, unit="count"
                ),
                "average_VipAvailability": AzureMetric(
                    name="VipAvailability", aggregation="average", value=100.0, unit="count"
                ),
                "average_DipAvailability": AzureMetric(
                    name="DipAvailability", aggregation="average", value=50.0, unit="count"
                ),
            },
            subscription="f00",
        ),
        name="az-lbe-001",
        frontend_ip_configs={
            "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001": FrontendIpConfiguration(
                id="/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001",
                name="az-frontend-ip-lb-001",
                privateIPAllocationMethod="Dynamic",
                privateIPAddress=None,
                public_ip_address=PublicIP(
                    name="10.1.1.1",
                    location="eastus",
                    ipAddress="20.199.181.70",
                    publicIPAllocationMethod="Static",
                    dns_fqdn="",
                ),
            )
        },
        inbound_nat_rules=[
            InboundNatRule(
                name="az-lbe-nat-in-rule-001",
                frontendIPConfiguration={
                    "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"
                },
                frontendPort=6556,
                backendPort=6556,
                backend_ip_config=BackendIpConfiguration(
                    name="vm837-nic-conf",
                    privateIPAddress="10.10.10.236",
                    privateIPAllocationMethod="Static",
                ),
            ),
            InboundNatRule(
                name="az-lbe-nat-in-rule-002",
                frontendIPConfiguration={
                    "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"
                },
                frontendPort=6557,
                backendPort=6557,
                backend_ip_config=BackendIpConfiguration(
                    name="vm838-nic-conf",
                    privateIPAddress="10.10.10.237",
                    privateIPAllocationMethod="Static",
                ),
            ),
        ],
        backend_pools={
            "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01": LoadBalancerBackendPool(
                id="/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01",
                name="az-lbe-001-backendpool01",
                addresses=[
                    LoadBalancerBackendAddress(
                        name="nic-config-346",
                        privateIPAddress="10.27.145.4",
                        privateIPAllocationMethod="Static",
                        primary=True,
                    ),
                    LoadBalancerBackendAddress(
                        name="az-vm-184-nic-config",
                        privateIPAddress="10.27.144.40",
                        privateIPAllocationMethod="Static",
                        primary=True,
                    ),
                ],
            )
        },
        outbound_rules=[
            OutboundRule(
                name="az-out-all-001",
                protocol="All",
                idleTimeoutInMinutes=4,
                backendAddressPool={
                    "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01"
                },
            ),
            OutboundRule(
                name="az-out-all-002",
                protocol="All",
                idleTimeoutInMinutes=4,
                backendAddressPool={
                    "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool02"
                },
            ),
        ],
    )
}

SECTION_NO_METRICS = {
    "az-lbe-001": LoadBalancer(
        resource=Resource(
            id="/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001",
            name="az-lbe-001",
            type="Microsoft.Network/loadBalancers",
            group="az-rg-lbe-001",
            kind=None,
            location="fijieast",
            tags={},
            properties={},
            specific_info={},
            metrics={},
            subscription="f00",
        ),
        name="az-lbe-001",
        frontend_ip_configs={},
        inbound_nat_rules=[],
        backend_pools={},
        outbound_rules=[],
    )
}


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        (
            [
                ["Resource"],
                [
                    '{"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001", "name": "az-lbe-001", "type": "Microsoft.Network/loadBalancers", "location": "fijieast", "subscription": "f00", "group": "az-rg-lbe-001", "provider": "Microsoft.Network", "properties": {"frontend_ip_configs": {"/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001": {"name": "az-frontend-ip-lb-001", "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001", "privateIPAllocationMethod": "Dynamic", "public_ip_address": {"dns_fqdn": "", "name": "10.1.1.1", "location": "eastus", "ipAddress": "20.199.181.70", "publicIPAllocationMethod": "Static"}}}, "inbound_nat_rules": [{"name": "az-lbe-nat-in-rule-001", "frontendIPConfiguration": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"}, "frontendPort": 6556, "backendPort": 6556, "backend_ip_config": {"name": "vm837-nic-conf", "privateIPAddress": "10.10.10.236", "privateIPAllocationMethod": "Static"}}, {"name": "az-lbe-nat-in-rule-002", "frontendIPConfiguration": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/frontendIPConfigurations/az-frontend-ip-lb-001"}, "frontendPort": 6557, "backendPort": 6557, "backend_ip_config": {"name": "vm838-nic-conf", "privateIPAddress": "10.10.10.237", "privateIPAllocationMethod": "Static"}}], "backend_pools": {"/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01": {"name": "az-lbe-001-backendpool01", "id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01", "addresses": [{"name": "nic-config-346", "privateIPAddress": "10.27.145.4", "privateIPAllocationMethod": "Static", "primary": true}, {"name": "az-vm-184-nic-config", "privateIPAddress": "10.27.144.40", "privateIPAllocationMethod": "Static", "primary": true}]}}, "outbound_rules": [{"name": "az-out-all-001", "protocol": "All", "idleTimeoutInMinutes": 4, "backendAddressPool": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool01"}}, {"name": "az-out-all-002", "protocol": "All", "idleTimeoutInMinutes": 4, "backendAddressPool": {"id": "/subscriptions/f00/resourceGroups/az-rg-lbe-001/providers/Microsoft.Network/loadBalancers/az-lbe-001/backendAddressPools/az-lbe-001-backendpool02"}}]}}'
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
            SECTION,
        )
    ],
)
def test_parse_load_balancer(string_table: StringTable, expected_section: Section) -> None:
    assert parse_load_balancer(string_table) == expected_section


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            SECTION,
            "az-lbe-001",
            {"lower_levels": (300, 100), "upper_levels": (100000, 500000)},
            [
                Result(
                    state=State.WARN,
                    summary="Bytes transmitted: 250 B/s (warn/crit below 300 B/s/100 B/s)",
                ),
                Metric("byte_count", 250.0, levels=(100000.0, 500000.0)),
            ],
        ),
    ],
)
def test_check_byte_count(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_byte_count(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        pytest.param({}, "az-lbe-001", id="no_item_in_section"),
        pytest.param(
            SECTION_NO_METRICS,
            "az-lbe-001",
            id="no_metric_in_section",
        ),
    ],
)
def test_check_byte_count_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_byte_count(item, {}, section))


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            SECTION,
            "az-lbe-001",
            {"upper_levels": (10, 20)},
            [
                Result(state=State.WARN, summary="SNAT usage: 18.75% (warn/crit at 10.00%/20.00%)"),
                Metric("snat_usage", 18.75, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Allocated SNAT ports: 16"),
                Metric("allocated_snat_ports", 16.0),
                Result(state=State.OK, summary="Used SNAT ports: 3"),
                Metric("used_snat_ports", 3.0),
            ],
            id="allocated_ports_not_0",
        ),
        pytest.param(
            {
                "az-lbe-001": LoadBalancer(
                    name="myLoadBalancer",
                    resource=Resource(
                        id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                        name="myLoadBalancer",
                        type="Microsoft.Network/loadBalancers",
                        group="CreatePubLBQS-rg",
                        kind=None,
                        location="westeurope",
                        tags={},
                        properties={},
                        specific_info={},
                        metrics={
                            "average_AllocatedSnatPorts": AzureMetric(
                                name="AllocatedSnatPorts",
                                aggregation="average",
                                value=0.0,
                                unit="count",
                            ),
                            "average_UsedSnatPorts": AzureMetric(
                                name="UsedSnatPorts", aggregation="average", value=3.0, unit="count"
                            ),
                        },
                        subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                    ),
                    frontend_ip_configs={},
                    inbound_nat_rules=[],
                    backend_pools={},
                    outbound_rules=[],
                )
            },
            "az-lbe-001",
            {},
            [
                Result(state=State.OK, summary="Allocated SNAT ports: 0"),
                Metric("allocated_snat_ports", 0.0),
                Result(state=State.OK, summary="Used SNAT ports: 3"),
                Metric("used_snat_ports", 3.0),
            ],
            id="allocated_ports_is_0",
        ),
    ],
)
def test_check_snat(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_snat(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        pytest.param({}, "az-lbe-001", id="no_item_in_section"),
        pytest.param(
            SECTION_NO_METRICS,
            "az-lbe-001",
            id="no_metric_in_section",
        ),
    ],
)
def test_check_snat_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_snat(item, {}, section))


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            SECTION,
            "az-lbe-001",
            {"vip_availability": (90.0, 25.0), "health_probe": (90.0, 25.0)},
            [
                Result(
                    state=State.OK,
                    summary="Data path availability: 100.00%",
                ),
                Metric("availability", 100.0),
                Result(
                    state=State.WARN,
                    summary="Health probe status: 50.00% (warn/crit below 90.00%/25.00%)",
                ),
                Metric("health_perc", 50.0),
            ],
        ),
    ],
)
def test_check_health(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_health(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        pytest.param({}, "az-lbe-001", id="no_item_in_section"),
        pytest.param(
            SECTION_NO_METRICS,
            "az-lbe-001",
            id="no_metric_in_section",
        ),
    ],
)
def test_check_health_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_health(item, {}, section))
