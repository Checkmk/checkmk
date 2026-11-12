#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Mapping, Sequence
from unittest.mock import AsyncMock

import pytest

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    AzureResource,
    get_backend_address_pools,
    get_frontend_ip_configs,
    get_inbound_nat_rules,
    get_remote_peerings,
    process_bulk_resources,
    process_virtual_net_gw,
    TagsImportPatternOption,
    UniqueHostnamesConfig,
)
from cmk.plugins.azure_v2.special_agent.azure_api_client import (
    ApiErrorMissingData,
    BaseAsyncApiClient,
)

from .lib import fake_azure_subscription

_NETWORK = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network"
_NETWORK_URI = "resourceGroups/rg/providers/Microsoft.Network"
_NIC_IP_CONFIG = f"{_NETWORK}/networkInterfaces/nic/ipConfigurations/ipconfig1"
_NIC_IP_CONFIG_URI = f"{_NETWORK_URI}/networkInterfaces/nic/ipConfigurations/ipconfig1"
_VMSS_NIC_IP_CONFIG = (
    "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachineScaleSets/"
    "vmss/virtualMachines/0/networkInterfaces/nic/ipConfigurations/ipconfig1"
)
_VMSS_NIC_IP_CONFIG_URI = (
    "resourceGroups/rg/providers/microsoft.Compute/virtualMachineScaleSets/"
    "vmss/virtualMachines/0/networkInterfaces/nic/ipConfigurations/ipconfig1"
)
_PUBLIC_IP = f"{_NETWORK}/publicIPAddresses/pip"
_PUBLIC_IP_URI = f"{_NETWORK_URI}/publicIPAddresses/pip"


def _api_client(answers: Mapping[str, object]) -> AsyncMock:
    async def get_async(uri_end: str, **_kwargs: object) -> object:
        answer = answers[uri_end]
        if isinstance(answer, Exception):
            raise answer
        return answer

    api_client = AsyncMock(spec=BaseAsyncApiClient)
    api_client.get_async.side_effect = get_async
    return api_client


def _resource(resource_id: str, resource_type: str) -> AzureResource:
    return AzureResource(
        {
            "id": resource_id,
            "name": resource_id.rsplit("/", 1)[-1],
            "type": resource_type,
            "location": "westeurope",
            "tags": {},
            "group": "rg",
        },
        TagsImportPatternOption.import_all,
        fake_azure_subscription(),
        UniqueHostnamesConfig(),
    )


def _public_ip_answer(dns_settings: Mapping[str, str] | None) -> Mapping[str, object]:
    properties: dict[str, object] = {
        "ipAddress": "20.1.2.3",
        "publicIPAllocationMethod": "Static",
    }
    if dns_settings is not None:
        properties["dnsSettings"] = dns_settings
    return {"name": "pip", "location": "westeurope", "properties": properties}


def _frontend_ip_config(**properties: object) -> Mapping[str, object]:
    return {
        "id": f"{_NETWORK}/loadBalancers/lb/frontendIPConfigurations/frontend",
        "name": "frontend",
        "properties": properties,
    }


_NIC_ANSWER = {
    "name": "ipconfig1",
    "properties": {
        "privateIPAddress": "10.0.0.4",
        "privateIPAllocationMethod": "Dynamic",
        "primary": True,
    },
}
_BACKEND_ADDRESS = {
    "name": "ipconfig1",
    "privateIPAddress": "10.0.0.4",
    "privateIPAllocationMethod": "Dynamic",
    "primary": True,
}


@pytest.mark.parametrize(
    "dns_settings, expected_fqdn",
    [
        pytest.param(
            {"fqdn": "app.westeurope.cloudapp.azure.com"},
            "app.westeurope.cloudapp.azure.com",
            id="with DNS name",
        ),
        pytest.param(None, "", id="without DNS name"),
    ],
)
@pytest.mark.asyncio
async def test_frontend_with_public_ip_gets_the_address_details(
    dns_settings: Mapping[str, str] | None, expected_fqdn: str
) -> None:
    resource = {
        "properties": {
            "frontendIPConfigurations": [
                _frontend_ip_config(
                    privateIPAllocationMethod="Dynamic", publicIPAddress={"id": _PUBLIC_IP}
                )
            ]
        }
    }
    api_client = _api_client({_PUBLIC_IP_URI: _public_ip_answer(dns_settings)})

    configs = await get_frontend_ip_configs(api_client, resource)

    assert list(configs.values()) == [
        {
            "id": f"{_NETWORK}/loadBalancers/lb/frontendIPConfigurations/frontend",
            "name": "frontend",
            "privateIPAllocationMethod": "Dynamic",
            "public_ip_address": {
                "dns_fqdn": expected_fqdn,
                "name": "pip",
                "location": "westeurope",
                "ipAddress": "20.1.2.3",
                "publicIPAllocationMethod": "Static",
            },
        }
    ]


@pytest.mark.asyncio
async def test_private_frontend_keeps_only_its_private_address() -> None:
    resource = {
        "properties": {
            "frontendIPConfigurations": [
                _frontend_ip_config(
                    privateIPAllocationMethod="Static", privateIPAddress="10.0.0.10"
                )
            ]
        }
    }

    configs = await get_frontend_ip_configs(_api_client({}), resource)

    assert list(configs.values()) == [
        {
            "id": f"{_NETWORK}/loadBalancers/lb/frontendIPConfigurations/frontend",
            "name": "frontend",
            "privateIPAllocationMethod": "Static",
            "privateIPAddress": "10.0.0.10",
        }
    ]


@pytest.mark.asyncio
async def test_inbound_nat_rule_gets_the_backend_address() -> None:
    load_balancer = {
        "properties": {
            "inboundNatRules": [
                {
                    "name": "ssh",
                    "properties": {
                        "frontendPort": 2222,
                        "backendPort": 22,
                        "backendIPConfiguration": {"id": _NIC_IP_CONFIG},
                    },
                }
            ]
        }
    }

    rules = await get_inbound_nat_rules(
        _api_client({_NIC_IP_CONFIG_URI: _NIC_ANSWER}), load_balancer
    )

    assert rules == [
        {
            "name": "ssh",
            "frontendPort": 2222,
            "backendPort": 22,
            "backend_ip_config": _BACKEND_ADDRESS,
        }
    ]


@pytest.mark.asyncio
async def test_backend_pool_lists_the_addresses_of_plain_and_scale_set_nics() -> None:
    load_balancer = {
        "properties": {
            "backendAddressPools": [
                {
                    "id": "pool_id",
                    "name": "pool",
                    "properties": {
                        "loadBalancerBackendAddresses": [
                            {"properties": {"networkInterfaceIPConfiguration": {"id": nic}}}
                            for nic in (_NIC_IP_CONFIG, _VMSS_NIC_IP_CONFIG)
                        ]
                    },
                }
            ]
        }
    }
    api_client = _api_client(
        {_NIC_IP_CONFIG_URI: _NIC_ANSWER, _VMSS_NIC_IP_CONFIG_URI: _NIC_ANSWER}
    )

    pools = await get_backend_address_pools(api_client, load_balancer)

    assert pools == [
        {"id": "pool_id", "name": "pool", "addresses": [_BACKEND_ADDRESS, _BACKEND_ADDRESS]}
    ]


@pytest.mark.asyncio
async def test_backend_address_without_nic_details_is_left_out() -> None:
    load_balancer = {
        "properties": {
            "backendAddressPools": [
                {
                    "id": "pool_id",
                    "name": "pool",
                    "properties": {
                        "loadBalancerBackendAddresses": [
                            {
                                "properties": {
                                    "networkInterfaceIPConfiguration": {"id": _NIC_IP_CONFIG}
                                }
                            }
                        ]
                    },
                }
            ]
        }
    }

    pools = await get_backend_address_pools(_api_client({_NIC_IP_CONFIG_URI: {}}), load_balancer)

    assert pools == [{"id": "pool_id", "name": "pool", "addresses": []}]


def _peering_id(subscription: str) -> str:
    return (
        f"/subscriptions/{subscription}/resourceGroups/rg/providers/Microsoft.Network/"
        "virtualNetworks/vnet/virtualNetworkPeerings/peering"
    )


_PEERING_URI = "resourceGroups/rg/providers/microsoft.network/virtualNetworks/vnet/virtualNetworkPeerings/peering"
_PEERING_ANSWER = {
    "name": "peering",
    "properties": {"peeringState": "Connected", "peeringSyncLevel": "FullyInSync"},
}
_GATEWAY_ID = f"{_NETWORK}/virtualNetworkGateways/gw"


@pytest.mark.asyncio
async def test_peerings_to_other_subscriptions_are_skipped() -> None:
    gateway = {
        "id": _GATEWAY_ID,
        "properties": {
            "remoteVirtualNetworkPeerings": [
                {"id": _peering_id("sub")},
                {"id": _peering_id("other_sub")},
            ]
        },
    }

    peerings = await get_remote_peerings(_api_client({_PEERING_URI: _PEERING_ANSWER}), gateway)

    assert peerings == [
        {"name": "peering", "peeringState": "Connected", "peeringSyncLevel": "FullyInSync"}
    ]


@pytest.mark.asyncio
async def test_virtual_network_gateway_gets_settings_peerings_and_health() -> None:
    resource = _resource(_GATEWAY_ID, "Microsoft.Network/virtualNetworkGateways")
    api_client = _api_client(
        {
            f"{_NETWORK_URI}/virtualNetworkGateways/gw": {
                "id": _GATEWAY_ID,
                "properties": {
                    "gatewayType": "Vpn",
                    "vpnType": "RouteBased",
                    "activeActive": False,
                    "enableBgp": False,
                    "remoteVirtualNetworkPeerings": [{"id": _peering_id("sub")}],
                },
            },
            _PEERING_URI: _PEERING_ANSWER,
            (
                "resourceGroups/rg/providers/microsoft.network/virtualNetworkGateways/gw/providers/"
                "Microsoft.ResourceHealth/availabilityStatuses/current"
            ): {"properties": {"availabilityState": "Available", "summary": "No problems"}},
        }
    )

    await process_virtual_net_gw(api_client, resource)

    assert (resource.info["specific_info"], resource.info["properties"]) == (
        {"gatewayType": "Vpn", "vpnType": "RouteBased", "activeActive": False, "enableBgp": False},
        {
            "remote_vnet_peerings": [
                {"name": "peering", "peeringState": "Connected", "peeringSyncLevel": "FullyInSync"}
            ],
            "health": {"availabilityState": "Available", "summary": "No problems"},
        },
    )


async def _process_bulk(
    api_client: AsyncMock,
    resource_type: str,
    resources: Sequence[AzureResource],
    *,
    debug: bool = True,
) -> None:
    for section in await process_bulk_resources(
        api_client,
        argparse.Namespace(debug=debug, otel_resource_types=[]),
        {},
        {resource_type},
        {resource.info["id"].lower(): resource for resource in resources},
        fake_azure_subscription(),
    ):
        section.write()


_APP_GATEWAY_ID = f"{_NETWORK}/applicationGateways/agw"


@pytest.mark.asyncio
async def test_app_gateway_gets_its_listeners_rules_and_backends() -> None:
    resource = _resource(_APP_GATEWAY_ID, "Microsoft.Network/applicationGateways")
    app_gateway = {
        "id": _APP_GATEWAY_ID,
        "properties": {
            "operationalState": "Running",
            "requestRoutingRules": [
                {"name": "rule", "properties": {"httpListener": {"id": "listener_id"}}}
            ],
            "httpListeners": [
                {"id": "listener_id", "name": "listener", "properties": {"protocol": "Https"}}
            ],
            "webApplicationFirewallConfiguration": {"enabled": True},
            "frontendPorts": [{"id": "port_id", "properties": {"port": 443}}],
            "backendHttpSettingsCollection": [
                {"id": "settings_id", "name": "settings", "properties": {"port": 80}}
            ],
            "backendAddressPools": [{"id": "pool_id", "name": "pool"}],
            "frontendIPConfigurations": [],
        },
    }
    api_client = _api_client({"providers/Microsoft.Network/applicationGateways": [app_gateway]})

    await _process_bulk(api_client, "Microsoft.Network/applicationGateways", [resource])

    assert resource.info["properties"] == {
        "operational_state": "Running",
        "routing_rules": [{"name": "rule", "httpListener": {"id": "listener_id"}}],
        "http_listeners": {
            "listener_id": {"id": "listener_id", "name": "listener", "protocol": "Https"}
        },
        "waf_enabled": True,
        "frontend_ports": {"port_id": {"port": 443}},
        "backend_settings": {"settings_id": {"name": "settings", "port": 80}},
        "backend_address_pools": {"pool_id": {"id": "pool_id", "name": "pool"}},
        "frontend_api_configs": {},
    }


_LOAD_BALANCER_ID = f"{_NETWORK}/loadBalancers/lb"


def _load_balancer_answer(**extra_properties: object) -> Mapping[str, object]:
    return {
        "id": _LOAD_BALANCER_ID,
        "properties": {
            "frontendIPConfigurations": [
                _frontend_ip_config(publicIPAddress={"id": _PUBLIC_IP}),
            ],
            "inboundNatRules": [],
            "backendAddressPools": [
                {"id": "pool_id", "name": "pool", "properties": {}},
            ],
            **extra_properties,
        },
    }


@pytest.mark.asyncio
async def test_load_balancer_gets_frontends_pools_and_outbound_rules() -> None:
    resource = _resource(_LOAD_BALANCER_ID, "Microsoft.Network/loadBalancers")
    load_balancer = _load_balancer_answer(
        outboundRules=[
            {"name": "out", "properties": {"protocol": "All", "idleTimeoutInMinutes": 4}}
        ]
    )
    api_client = _api_client(
        {
            "providers/Microsoft.Network/loadBalancers": [load_balancer],
            _PUBLIC_IP_URI: _public_ip_answer(None),
        }
    )

    await _process_bulk(api_client, "Microsoft.Network/loadBalancers", [resource])

    assert resource.info["properties"] == {
        "frontend_ip_configs": {
            f"{_NETWORK}/loadBalancers/lb/frontendIPConfigurations/frontend": {
                "id": f"{_NETWORK}/loadBalancers/lb/frontendIPConfigurations/frontend",
                "name": "frontend",
                "public_ip_address": {
                    "dns_fqdn": "",
                    "name": "pip",
                    "location": "westeurope",
                    "ipAddress": "20.1.2.3",
                    "publicIPAllocationMethod": "Static",
                },
            }
        },
        "inbound_nat_rules": [],
        "backend_pools": {"pool_id": {"id": "pool_id", "name": "pool", "addresses": []}},
        "outbound_rules": [{"name": "out", "protocol": "All", "idleTimeoutInMinutes": 4}],
    }


@pytest.mark.asyncio
async def test_failed_load_balancer_lookup_is_shown_in_agent_info(
    capsys: pytest.CaptureFixture[str],
) -> None:
    resource = _resource(_LOAD_BALANCER_ID, "Microsoft.Network/loadBalancers")
    api_client = _api_client(
        {
            "providers/Microsoft.Network/loadBalancers": [_load_balancer_answer()],
            _PUBLIC_IP_URI: ApiErrorMissingData("public IP not found"),
        }
    )

    await _process_bulk(api_client, "Microsoft.Network/loadBalancers", [resource], debug=False)

    output = capsys.readouterr().out
    assert "<<<azure_v2_agent_info" in output
    assert _LOAD_BALANCER_ID in output


@pytest.mark.asyncio
async def test_failed_load_balancer_lookup_raises_in_debug_mode() -> None:
    resource = _resource(_LOAD_BALANCER_ID, "Microsoft.Network/loadBalancers")
    api_client = _api_client(
        {
            "providers/Microsoft.Network/loadBalancers": [_load_balancer_answer()],
            _PUBLIC_IP_URI: ApiErrorMissingData("public IP not found"),
        }
    )

    with pytest.raises(ApiErrorMissingData, match="Failed to collect data for load balancer"):
        await _process_bulk(api_client, "Microsoft.Network/loadBalancers", [resource])


@pytest.mark.asyncio
async def test_monitored_firewall_gets_a_section(capsys: pytest.CaptureFixture[str]) -> None:
    firewall_id = f"{_NETWORK}/azureFirewalls/fw"
    resource = _resource(firewall_id, "Microsoft.Network/azureFirewalls")
    api_client = _api_client({"providers/Microsoft.Network/azureFirewalls": [{"id": firewall_id}]})

    await _process_bulk(api_client, "Microsoft.Network/azureFirewalls", [resource])

    assert "<<<<fw>>>>\n<<<azure_v2_azurefirewalls:sep(124)>>>" in capsys.readouterr().out


@pytest.mark.parametrize(
    "resource_type, list_uri",
    [
        pytest.param(
            "Microsoft.Network/applicationGateways",
            "providers/Microsoft.Network/applicationGateways",
            id="application gateway",
        ),
        pytest.param(
            "Microsoft.Network/loadBalancers",
            "providers/Microsoft.Network/loadBalancers",
            id="load balancer",
        ),
        pytest.param(
            "Microsoft.Network/azureFirewalls",
            "providers/Microsoft.Network/azureFirewalls",
            id="firewall",
        ),
    ],
)
@pytest.mark.asyncio
async def test_unmonitored_network_resource_gets_no_section(
    resource_type: str, list_uri: str, capsys: pytest.CaptureFixture[str]
) -> None:
    api_client = _api_client({list_uri: [{"id": f"{_NETWORK}/other/filtered_out"}]})

    await _process_bulk(api_client, resource_type, [])

    assert capsys.readouterr().out == ""
