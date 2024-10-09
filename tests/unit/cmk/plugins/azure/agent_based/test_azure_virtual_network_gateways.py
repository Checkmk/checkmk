#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.azure.agent_based.azure_virtual_network_gateways import (
    BgpSettings,
    check_azure_virtual_network_gateway,
    check_virtual_network_gateway_bgp,
    check_virtual_network_gateway_health,
    check_virtual_network_gateway_peering,
    check_virtual_network_gateway_settings,
    discover_virtual_network_gateway,
    discover_virtual_network_gateway_peering,
    parse_virtual_network_gateway,
    PeeringAddresses,
    RemoteVnetPeering,
    Section,
    VNetGateway,
    VNetGWHealth,
    VNetGWSettings,
)
from cmk.plugins.lib.azure import AzureMetric, Resource

SECTION: Section = {
    "vpn-001": VNetGateway(
        resource=Resource(
            id="/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001",
            name="vpn-001",
            type="Microsoft.Network/virtualNetworkGateways",
            group="rg-vpn-1",
            kind=None,
            location="maxwellmonteswest",
            tags={},
            properties={
                "health": {
                    "availabilityState": "Available",
                    "summary": "This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
                    "reasonType": "",
                    "occuredTime": "2022-06-27T21:25:58Z",
                },
                "remote_vnet_peerings": [
                    {
                        "name": "vnet-peering-1",
                        "peeringState": "Connected",
                        "peeringSyncLevel": "FullyInSync",
                    }
                ],
            },
            specific_info={
                "bgpSettings": {
                    "asn": 65149,
                    "bgpPeeringAddress": "10.31.128.132,10.31.128.133",
                    "peerWeight": 0,
                    "bgpPeeringAddresses": [
                        {
                            "ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/vnetConf0",
                            "defaultBgpIpAddresses": ["10.31.128.132"],
                            "customBgpIpAddresses": [],
                            "tunnelIpAddresses": ["11.22.33.44"],
                        },
                        {
                            "ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/ActAct",
                            "defaultBgpIpAddresses": ["10.31.128.133"],
                            "customBgpIpAddresses": [],
                            "tunnelIpAddresses": ["55.66.77.88"],
                        },
                    ],
                },
                "gatewayType": "Vpn",
                "vpnType": "RouteBased",
                "enableBgp": True,
                "activeActive": True,
                "disableIPSecReplayProtection": False,
            },
            metrics={
                "average_AverageBandwidth": AzureMetric(
                    name="AverageBandwidth",
                    aggregation="average",
                    value=13729.0,
                    unit="bytes_per_second",
                ),
                "average_P2SBandwidth": AzureMetric(
                    name="P2SBandwidth", aggregation="average", value=0.0, unit="bytes_per_second"
                ),
                "maximum_P2SConnectionCount": AzureMetric(
                    name="P2SConnectionCount", aggregation="maximum", value=1.0, unit="count"
                ),
                "count_TunnelIngressBytes": AzureMetric(
                    name="TunnelIngressBytes", aggregation="count", value=4.0, unit="bytes"
                ),
                "count_TunnelEgressBytes": AzureMetric(
                    name="TunnelEgressBytes", aggregation="count", value=4.0, unit="bytes"
                ),
                "count_TunnelIngressPacketDropCount": AzureMetric(
                    name="TunnelIngressPacketDropCount",
                    aggregation="count",
                    value=4.0,
                    unit="count",
                ),
                "count_TunnelEgressPacketDropCount": AzureMetric(
                    name="TunnelEgressPacketDropCount", aggregation="count", value=4.0, unit="count"
                ),
            },
            subscription="xyz",
        ),
        remote_vnet_peerings=[
            RemoteVnetPeering(
                name="vnet-peering-1", peeringState="Connected", peeringSyncLevel="FullyInSync"
            )
        ],
        health=VNetGWHealth(
            availabilityState="Available",
            summary="This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
            reasonType="",
            occuredTime="2022-06-27T21:25:58Z",
        ),
        settings=VNetGWSettings(
            disableIPSecReplayProtection=False,
            gatewayType="Vpn",
            vpnType="RouteBased",
            activeActive=True,
            enableBgp=True,
            bgpSettings=BgpSettings(
                asn=65149,
                peerWeight=0,
                bgpPeeringAddresses=[
                    PeeringAddresses(
                        defaultBgpIpAddresses=["10.31.128.132"],
                        customBgpIpAddresses=[],
                        tunnelIpAddresses=["11.22.33.44"],
                    ),
                    PeeringAddresses(
                        defaultBgpIpAddresses=["10.31.128.133"],
                        customBgpIpAddresses=[],
                        tunnelIpAddresses=["55.66.77.88"],
                    ),
                ],
            ),
        ),
    )
}

SECTION_HEALTH_NOT_AVAILABLE = {
    "vpn-001": VNetGateway(
        resource=Resource(
            id="/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001",
            name="vpn-001",
            type="Microsoft.Network/virtualNetworkGateways",
            group="rg-vpn-1",
            kind=None,
            location="maxwellmonteswest",
            tags={},
            properties={},
            specific_info={},
            metrics={},
            subscription="xyz",
        ),
        remote_vnet_peerings=[
            RemoteVnetPeering(
                name="vnet-peering-1", peeringState="Connected", peeringSyncLevel="FullyInSync"
            )
        ],
        health=VNetGWHealth(
            availabilityState="Not available",
            summary="This gateway isn't running.",
            reasonType="Error",
            occuredTime="2022-06-27T21:25:58Z",
        ),
        settings=VNetGWSettings(
            disableIPSecReplayProtection=False,
            gatewayType="Vpn",
            vpnType="RouteBased",
            activeActive=True,
            enableBgp=True,
            bgpSettings=BgpSettings(
                asn=65149,
                peerWeight=0,
                bgpPeeringAddresses=[
                    PeeringAddresses(
                        defaultBgpIpAddresses=["10.31.128.132"],
                        customBgpIpAddresses=[],
                        tunnelIpAddresses=["11.22.33.44"],
                    ),
                ],
            ),
        ),
    )
}

SECTION_BGP_DISABLED = {
    "vpn-001": VNetGateway(
        resource=Resource(
            id="/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001",
            name="vpn-001",
            type="Microsoft.Network/virtualNetworkGateways",
            group="rg-vpn-1",
            kind=None,
            location="maxwellmonteswest",
            tags={},
            properties={},
            specific_info={},
            metrics={},
            subscription="xyz",
        ),
        remote_vnet_peerings=[
            RemoteVnetPeering(
                name="vnet-peering-1", peeringState="Connected", peeringSyncLevel="FullyInSync"
            )
        ],
        health=VNetGWHealth(
            availabilityState="Not available",
            summary="This gateway isn't running.",
            reasonType="Error",
            occuredTime="2022-06-27T21:25:58Z",
        ),
        settings=VNetGWSettings(
            disableIPSecReplayProtection=False,
            gatewayType="Vpn",
            vpnType="RouteBased",
            activeActive=True,
            enableBgp=False,
        ),
    )
}

SECTION_PEERING_DISCONNECTED = {
    "vpn-001": VNetGateway(
        resource=Resource(
            id="/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001",
            name="vpn-001",
            type="Microsoft.Network/virtualNetworkGateways",
            group="rg-vpn-1",
            kind=None,
            location="maxwellmonteswest",
            tags={},
            properties={},
            specific_info={},
            metrics={},
            subscription="xyz",
        ),
        remote_vnet_peerings=[
            RemoteVnetPeering(
                name="vnet-peering-1", peeringState="Disconnected", peeringSyncLevel="FullyInSync"
            )
        ],
        health=VNetGWHealth(
            availabilityState="Not available",
            summary="This gateway isn't running.",
            reasonType="Error",
            occuredTime="2022-06-27T21:25:58Z",
        ),
        settings=VNetGWSettings(
            disableIPSecReplayProtection=False,
            gatewayType="Vpn",
            vpnType="RouteBased",
            activeActive=True,
            enableBgp=False,
        ),
    )
}

SECTION_WITH_MISSING_PEER_ADDRESSES = {
    "vpn-001": VNetGateway(
        resource=Resource(
            id="/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001",
            name="vpn-001",
            type="Microsoft.Network/virtualNetworkGateways",
            group="rg-vpn-1",
            kind=None,
            location="maxwellmonteswest",
            tags={},
            properties={
                "health": {
                    "availabilityState": "Available",
                    "summary": "This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
                    "reasonType": "",
                    "occuredTime": "2022-06-27T21:25:58Z",
                },
                "remote_vnet_peerings": [
                    {
                        "name": "vnet-peering-1",
                        "peeringState": "Connected",
                        "peeringSyncLevel": "FullyInSync",
                    }
                ],
            },
            specific_info={
                "bgpSettings": {
                    "asn": 65149,
                    "bgpPeeringAddress": "10.31.128.132,10.31.128.133",
                    "peerWeight": 0,
                    "bgpPeeringAddresses": [
                        {
                            "ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/vnetConf0",
                            "tunnelIpAddresses": ["11.22.33.44"],
                        },
                        {
                            "ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/ActAct",
                            "defaultBgpIpAddresses": ["10.31.128.133"],
                            "customBgpIpAddresses": [],
                        },
                    ],
                },
                "gatewayType": "Vpn",
                "vpnType": "RouteBased",
                "enableBgp": True,
                "activeActive": True,
                "disableIPSecReplayProtection": False,
            },
            metrics={},
            subscription="xyz",
        ),
        remote_vnet_peerings=[
            RemoteVnetPeering(
                name="vnet-peering-1", peeringState="Connected", peeringSyncLevel="FullyInSync"
            )
        ],
        health=VNetGWHealth(
            availabilityState="Available",
            summary="This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
            reasonType="",
            occuredTime="2022-06-27T21:25:58Z",
        ),
        settings=VNetGWSettings(
            disableIPSecReplayProtection=False,
            gatewayType="Vpn",
            vpnType="RouteBased",
            activeActive=True,
            enableBgp=True,
            bgpSettings=BgpSettings(
                asn=65149,
                peerWeight=0,
                bgpPeeringAddresses=[
                    PeeringAddresses(
                        defaultBgpIpAddresses=[],
                        customBgpIpAddresses=[],
                        tunnelIpAddresses=["11.22.33.44"],
                    ),
                    PeeringAddresses(
                        defaultBgpIpAddresses=["10.31.128.133"],
                        customBgpIpAddresses=[],
                        tunnelIpAddresses=[],
                    ),
                ],
            ),
        ),
    )
}

SECTION_WITHOUT_PEER_ADDRESSES = {
    "vpn-001": VNetGateway(
        resource=Resource(
            id="/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001",
            name="vpn-001",
            type="Microsoft.Network/virtualNetworkGateways",
            group="rg-vpn-1",
            kind=None,
            location="maxwellmonteswest",
            tags={},
            properties={
                "health": {
                    "availabilityState": "Available",
                    "summary": "This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
                    "reasonType": "",
                    "occuredTime": "2022-06-27T21:25:58Z",
                },
                "remote_vnet_peerings": [
                    {
                        "name": "vnet-peering-1",
                        "peeringState": "Connected",
                        "peeringSyncLevel": "FullyInSync",
                    }
                ],
            },
            specific_info={
                "bgpSettings": {
                    "asn": 65149,
                    "bgpPeeringAddress": "10.31.128.132,10.31.128.133",
                    "peerWeight": 0,
                },
                "gatewayType": "Vpn",
                "vpnType": "RouteBased",
                "enableBgp": True,
                "activeActive": True,
                "disableIPSecReplayProtection": False,
            },
            metrics={},
            subscription="xyz",
        ),
        remote_vnet_peerings=[
            RemoteVnetPeering(
                name="vnet-peering-1", peeringState="Connected", peeringSyncLevel="FullyInSync"
            )
        ],
        health=VNetGWHealth(
            availabilityState="Available",
            summary="This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
            reasonType="",
            occuredTime="2022-06-27T21:25:58Z",
        ),
        settings=VNetGWSettings(
            disableIPSecReplayProtection=False,
            gatewayType="Vpn",
            vpnType="RouteBased",
            activeActive=True,
            enableBgp=True,
            bgpSettings=BgpSettings(
                asn=65149,
                peerWeight=0,
                bgpPeeringAddresses=[],
            ),
        ),
    )
}


@pytest.mark.parametrize(
    "string_table,expected_parsed",
    [
        pytest.param(
            [
                ["Resource"],
                [
                    '{"id": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001", "name": "vpn-001", "type": "Microsoft.Network/virtualNetworkGateways", "location": "maxwellmonteswest", "subscription": "xyz", "group": "rg-vpn-1", "provider": "Microsoft.Network", "properties": {"health": {"availabilityState": "Available", "summary": "This gateway is running normally. There aren\\u2019t any known Azure platform problems affecting this gateway.", "reasonType": "", "occuredTime": "2022-06-27T21:25:58Z"}, "remote_vnet_peerings": [{"name": "vnet-peering-1", "peeringState": "Connected", "peeringSyncLevel": "FullyInSync"}]}, "specific_info": {"bgpSettings": {"asn": 65149, "bgpPeeringAddress": "10.31.128.132,10.31.128.133", "peerWeight": 0, "bgpPeeringAddresses": [{"ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/vnetConf0", "defaultBgpIpAddresses": ["10.31.128.132"], "customBgpIpAddresses": [], "tunnelIpAddresses": ["11.22.33.44"]}, {"ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/ActAct", "defaultBgpIpAddresses": ["10.31.128.133"], "customBgpIpAddresses": [], "tunnelIpAddresses": ["55.66.77.88"]}]}, "gatewayType": "Vpn", "vpnType": "RouteBased", "enableBgp": true, "activeActive": true, "disableIPSecReplayProtection": false}}'
                ],
                ["metrics following", "7"],
                [
                    '{"filter": null, "unit": "bytes_per_second", "name": "AverageBandwidth", "interval_id": "PT1M", "timestamp": "1545049860", "interval": "0:01:00", "aggregation": "average", "value": 13729.0}'
                ],
                [
                    '{"name": "P2SBandwidth", "aggregation": "average", "value": 0.0, "unit": "bytes_per_second", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter": null}'
                ],
                [
                    '{"name": "P2SConnectionCount", "aggregation": "maximum", "value": 1.0, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'
                ],
                [
                    '{"name": "TunnelIngressBytes", "aggregation": "count", "value": 4.0, "unit": "bytes", "timestamp": "2022-06-30T12:05:00Z", "filter": null, "interval_id": "PT5M", "interval": "0:05:00"}'
                ],
                [
                    '{"name": "TunnelEgressBytes", "aggregation": "count", "value": 4.0, "unit": "bytes", "timestamp": "2022-06-30T12:05:00Z", "filter": null, "interval_id": "PT5M", "interval": "0:05:00"}'
                ],
                [
                    '{"name": "TunnelIngressPacketDropCount", "aggregation": "count", "value": 4.0, "unit": "count", "timestamp": "2022-06-30T12:05:00Z", "filter": null, "interval_id": "PT5M", "interval": "0:05:00"}'
                ],
                [
                    '{"name": "TunnelEgressPacketDropCount", "aggregation": "count", "value": 4.0, "unit": "count", "timestamp": "2022-06-30T12:05:00Z", "filter": null, "interval_id": "PT5M", "interval": "0:05:00"}'
                ],
            ],
            SECTION,
            id="vnet gateway with metrics",
        ),
        pytest.param(
            [
                ["Resource"],
                [
                    '{"id": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001", "name": "vpn-001", "type": "Microsoft.Network/virtualNetworkGateways", "location": "maxwellmonteswest", "subscription": "xyz", "group": "rg-vpn-1", "provider": "Microsoft.Network", "properties": {"health": {"availabilityState": "Available", "summary": "This gateway is running normally. There aren\\u2019t any known Azure platform problems affecting this gateway.", "reasonType": "", "occuredTime": "2022-06-27T21:25:58Z"}, "remote_vnet_peerings": [{"name": "vnet-peering-1", "peeringState": "Connected", "peeringSyncLevel": "FullyInSync"}]}, "specific_info": {"bgpSettings": {"asn": 65149, "bgpPeeringAddress": "10.31.128.132,10.31.128.133", "peerWeight": 0, "bgpPeeringAddresses": [{"ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/vnetConf0", "tunnelIpAddresses": ["11.22.33.44"]}, {"ipconfigurationId": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001/ipConfigurations/ActAct", "defaultBgpIpAddresses": ["10.31.128.133"], "customBgpIpAddresses": []}]}, "gatewayType": "Vpn", "vpnType": "RouteBased", "enableBgp": true, "activeActive": true, "disableIPSecReplayProtection": false}}'
                ],
            ],
            SECTION_WITH_MISSING_PEER_ADDRESSES,
            id="vnet gateway with some peering addresses missing",
        ),
        pytest.param(
            [
                ["Resource"],
                [
                    '{"id": "/subscriptions/xyz/resourceGroups/rg-vpn-1/providers/Microsoft.Network/virtualNetworkGateways/vpn-001", "name": "vpn-001", "type": "Microsoft.Network/virtualNetworkGateways", "location": "maxwellmonteswest", "subscription": "xyz", "group": "rg-vpn-1", "provider": "Microsoft.Network", "properties": {"health": {"availabilityState": "Available", "summary": "This gateway is running normally. There aren\\u2019t any known Azure platform problems affecting this gateway.", "reasonType": "", "occuredTime": "2022-06-27T21:25:58Z"}, "remote_vnet_peerings": [{"name": "vnet-peering-1", "peeringState": "Connected", "peeringSyncLevel": "FullyInSync"}]}, "specific_info": {"bgpSettings": {"asn": 65149, "bgpPeeringAddress": "10.31.128.132,10.31.128.133", "peerWeight": 0}, "gatewayType": "Vpn", "vpnType": "RouteBased", "enableBgp": true, "activeActive": true, "disableIPSecReplayProtection": false}}'
                ],
            ],
            SECTION_WITHOUT_PEER_ADDRESSES,
            id="vnet gateway without peering addresses",
        ),
    ],
)
def test_parse_virtual_network_gateways(
    string_table: StringTable,
    expected_parsed: Section,
) -> None:
    assert parse_virtual_network_gateway(string_table) == expected_parsed


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        (
            SECTION,
            [Service(item="vpn-001")],
        ),
    ],
)
def test_discovery_virtual_network_gateways(
    section: Section,
    expected_discovery: Sequence[Service],
) -> None:
    assert list(discover_virtual_network_gateway(section)) == expected_discovery


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            SECTION,
            "vpn-001",
            {"s2s_bandwidth_levels_upper": (12000, 14000)},
            [
                Result(state=State.OK, summary="Point-to-site connections: 1"),
                Metric("connections", 1.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Point-to-site bandwidth: 0.00 B/s"),
                Metric("p2s_bandwidth", 0.0, boundaries=(0.0, None)),
                Result(
                    state=State.WARN,
                    summary="Site-to-site bandwidth: 13.7 kB/s (warn/crit at 12.0 kB/s/14.0 kB/s)",
                ),
                Metric("s2s_bandwidth", 13729.0, levels=(12000.0, 14000.0), boundaries=(0.0, None)),
                Result(state=State.OK, summary="Tunnel Ingress Bytes: 4 B"),
                Metric("ingress", 4.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Tunnel Egress Bytes: 4 B"),
                Metric("egress", 4.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Tunnel Ingress Packet Drop Count: 4"),
                Metric("ingress_packet_drop", 4.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Tunnel Egress Packet Drop Count: 4"),
                Metric("egress_packet_drop", 4.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Location: maxwellmonteswest"),
            ],
            id="item_present",
        ),
        pytest.param(SECTION, "unexpected-item", {}, [], id="item_not_found"),
    ],
)
def test_check_virtual_network_gateways(
    section: Section,
    item: str,
    params: Mapping[str, tuple[float, float]],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_azure_virtual_network_gateway(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            SECTION,
            "vpn-001",
            [
                Result(state=State.OK, summary="IPsec replay protection: on"),
                Result(state=State.OK, summary="VPN type: RouteBased, VPN gateway type: Vpn"),
                Result(state=State.OK, summary="active/active: True"),
            ],
            id="item_present",
        ),
        pytest.param(SECTION, "unexpected-item", [], id="item_not_found"),
    ],
)
def test_check_virtual_network_gateway_settings(section, item, expected_result):
    assert list(check_virtual_network_gateway_settings(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            SECTION,
            "vpn-001",
            [
                Result(state=State.OK, summary="Availability state: Available"),
                Result(
                    state=State.OK,
                    summary="Summary: This gateway is running normally. There aren’t any known Azure platform problems affecting this gateway.",
                ),
            ],
            id="state_available",
        ),
        pytest.param(
            SECTION_HEALTH_NOT_AVAILABLE,
            "vpn-001",
            [
                Result(state=State.OK, summary="Availability state: Not available"),
                Result(state=State.OK, summary="Summary: This gateway isn't running."),
                Result(
                    state=State.CRIT,
                    summary="Reason type: Error, Occurred time: 2022-06-27 21:25:58",
                ),
            ],
            id="state_not_available",
        ),
        pytest.param(SECTION, "unexpected-item", [], id="item_not_found"),
    ],
)
def test_check_virtual_network_gateway_health(section, item, expected_result):
    assert list(check_virtual_network_gateway_health(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            SECTION,
            "vpn-001",
            [
                Result(state=State.OK, summary="Enabled: True, ASN: 65149, Peer weight: 0"),
                Result(
                    state=State.OK,
                    summary="Default peering addresses: ['10.31.128.132', '10.31.128.133']",
                ),
                Result(state=State.OK, summary="Custom peering addresses: []"),
                Result(
                    state=State.OK,
                    summary="Tunnel peering addresses: ['11.22.33.44', '55.66.77.88']",
                ),
            ],
            id="bgp_enabled",
        ),
        pytest.param(
            SECTION_BGP_DISABLED,
            "vpn-001",
            [Result(state=State.OK, summary="Enabled: False")],
            id="bgp_disabled",
        ),
        pytest.param(SECTION, "unexpected-item", [], id="item_not_found"),
    ],
)
def test_check_virtual_network_gateway_bgp(section, item, expected_result):
    assert list(check_virtual_network_gateway_bgp(item, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        (
            SECTION,
            [Service(item="vpn-001 Remote Peering vnet-peering-1")],
        ),
    ],
)
def test_discover_virtual_network_gateway_peering(section, expected_discovery):
    assert list(discover_virtual_network_gateway_peering(section)) == expected_discovery


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            SECTION,
            "vpn-001 Remote Peering vnet-peering-1",
            [
                Result(
                    state=State.OK,
                    summary="Peering state: Connected, Peering sync level: FullyInSync",
                )
            ],
            id="peering_connected",
        ),
        pytest.param(
            SECTION_PEERING_DISCONNECTED,
            "vpn-001 Remote Peering vnet-peering-1",
            [
                Result(
                    state=State.WARN,
                    summary="Peering state: Disconnected, Peering sync level: FullyInSync",
                )
            ],
            id="peering_disconnected",
        ),
        pytest.param(
            SECTION, "unexpected-gw Remote Peering vnet-peering-1", [], id="gateway_not_found"
        ),
        pytest.param(
            SECTION, "vpn-001 Remote Peering unexpected-peering", [], id="peering_not_found"
        ),
    ],
)
def test_check_virtual_network_gateway_peering(section, item, expected_result):
    assert list(check_virtual_network_gateway_peering(item, section)) == expected_result
