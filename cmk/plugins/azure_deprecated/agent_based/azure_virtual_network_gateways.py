#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.azure import (
    create_check_metrics_function,
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    MetricData,
    parse_azure_datetime,
    parse_resources,
    Resource,
)


class PeeringAddresses(BaseModel):
    defaultBgpIpAddresses: Sequence[str] = []
    customBgpIpAddresses: Sequence[str] = []
    tunnelIpAddresses: Sequence[str] = []


class BgpSettings(BaseModel):
    asn: int
    peerWeight: int
    bgpPeeringAddresses: Sequence[PeeringAddresses] = []


class RemoteVnetPeering(BaseModel):
    name: str
    peeringState: str
    peeringSyncLevel: str


class VNetGWHealth(BaseModel):
    availabilityState: str
    summary: str
    reasonType: str
    occuredTime: str


class VNetGWSettings(BaseModel):
    disableIPSecReplayProtection: bool
    gatewayType: str
    vpnType: str
    activeActive: bool
    enableBgp: bool
    bgpSettings: BgpSettings | None = None


class VNetGateway(BaseModel):
    resource: Resource
    remote_vnet_peerings: Sequence[RemoteVnetPeering]
    health: VNetGWHealth
    settings: VNetGWSettings


Section = Mapping[str, VNetGateway]


def parse_virtual_network_gateway(string_table: StringTable) -> Section:
    section = {}
    resources = parse_resources(string_table)

    for name, resource in resources.items():
        section[name] = VNetGateway(
            resource=resource,
            remote_vnet_peerings=resource.properties["remote_vnet_peerings"],
            health=VNetGWHealth(**resource.properties["health"]),
            settings=VNetGWSettings(**resource.specific_info),
        )

    return section


agent_section_azure_virtualnetworkgateways = AgentSection(
    name="azure_virtualnetworkgateways",
    parse_function=parse_virtual_network_gateway,
)


#   .--VNet Gateway--------------------------------------------------------.
#   | __     ___   _      _      ____       _                              |
#   | \ \   / / \ | | ___| |_   / ___| __ _| |_ _____      ____ _ _   _    |
#   |  \ \ / /|  \| |/ _ \ __| | |  _ / _` | __/ _ \ \ /\ / / _` | | | |   |
#   |   \ V / | |\  |  __/ |_  | |_| | (_| | ||  __/\ V  V / (_| | |_| |   |
#   |    \_/  |_| \_|\___|\__|  \____|\__,_|\__\___| \_/\_/ \__,_|\__, |   |
#   |                                                             |___/    |
#   +----------------------------------------------------------------------+


def discover_virtual_network_gateway(section: Section) -> DiscoveryResult:
    for item, vnet_gateway in section.items():
        yield Service(
            item=item, labels=get_service_labels_from_resource_tags(vnet_gateway.resource.tags)
        )


def check_azure_virtual_network_gateway(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if (vn_gateway := section.get(item)) is None:
        return

    yield from create_check_metrics_function(
        [
            MetricData(
                "maximum_P2SConnectionCount",
                "connections",
                "Point-to-site connections",
                lambda v: str(int(v)),
                lower_levels_param="connections_levels_lower",
                upper_levels_param="connections_levels_upper",
                boundaries=(0, None),
            ),
            MetricData(
                "average_P2SBandwidth",
                "p2s_bandwidth",
                "Point-to-site bandwidth",
                render.iobandwidth,
                lower_levels_param="p2s_bandwidth_levels_lower",
                upper_levels_param="p2s_bandwidth_levels_upper",
                boundaries=(0, None),
            ),
            MetricData(
                "average_AverageBandwidth",
                "s2s_bandwidth",
                "Site-to-site bandwidth",
                render.iobandwidth,
                lower_levels_param="s2s_bandwidth_levels_lower",
                upper_levels_param="s2s_bandwidth_levels_upper",
                boundaries=(0, None),
            ),
            MetricData(
                "count_TunnelIngressBytes",
                "ingress",
                "Tunnel Ingress Bytes",
                render.bytes,
                upper_levels_param="ingress_levels",
                boundaries=(0, None),
            ),
            MetricData(
                "count_TunnelEgressBytes",
                "egress",
                "Tunnel Egress Bytes",
                render.bytes,
                upper_levels_param="egress_levels",
                boundaries=(0, None),
            ),
            MetricData(
                "count_TunnelIngressPacketDropCount",
                "ingress_packet_drop",
                "Tunnel Ingress Packet Drop Count",
                lambda v: str(int(v)),
                upper_levels_param="ingress_packet_drop_levels",
                boundaries=(0, None),
            ),
            MetricData(
                "count_TunnelEgressPacketDropCount",
                "egress_packet_drop",
                "Tunnel Egress Packet Drop Count",
                lambda v: str(int(v)),
                upper_levels_param="egress_packet_drop_levels",
                boundaries=(0, None),
            ),
        ],
        suppress_error=True,
    )(item, params, {item: vn_gateway.resource})

    for name, value in iter_resource_attributes(vn_gateway.resource):
        yield Result(state=State.OK, summary=f"{name}: {value}")


check_plugin_azure_virtual_network_gateways = CheckPlugin(
    name="azure_virtual_network_gateways",
    sections=["azure_virtualnetworkgateways"],
    service_name="VNet Gateway %s",
    discovery_function=discover_virtual_network_gateway,
    check_function=check_azure_virtual_network_gateway,
    check_ruleset_name="azure_virtualnetworkgateways",
    check_default_parameters={},
)


#   .--Settings------------------------------------------------------------.
#   |                ____       _   _   _                                  |
#   |               / ___|  ___| |_| |_(_)_ __   __ _ ___                  |
#   |               \___ \ / _ \ __| __| | '_ \ / _` / __|                 |
#   |                ___) |  __/ |_| |_| | | | | (_| \__ \                 |
#   |               |____/ \___|\__|\__|_|_| |_|\__, |___/                 |
#   |                                           |___/                      |
#   +----------------------------------------------------------------------+


def check_virtual_network_gateway_settings(item: str, section: Section) -> CheckResult:
    if (vn_gateway := section.get(item)) is None:
        return

    settings = vn_gateway.settings
    state = State.WARN if settings.disableIPSecReplayProtection else State.OK

    yield Result(
        state=state,
        summary=f"IPsec replay protection: {'off' if settings.disableIPSecReplayProtection else 'on'}",
    )
    yield Result(
        state=State.OK,
        summary=f"VPN type: {settings.vpnType}, VPN gateway type: {settings.gatewayType}",
    )
    yield Result(state=State.OK, summary=f"active/active: {settings.activeActive}")


check_plugin_azure_virtual_network_gateway_settings = CheckPlugin(
    name="azure_virtual_network_gateway_settings",
    sections=["azure_virtualnetworkgateways"],
    service_name="VNet Gateway %s Settings",
    discovery_function=discover_virtual_network_gateway,
    check_function=check_virtual_network_gateway_settings,
)


#   .--Health Probe--------------------------------------------------------.
#   |      _   _            _ _   _       ____            _                |
#   |     | | | | ___  __ _| | |_| |__   |  _ \ _ __ ___ | |__   ___       |
#   |     | |_| |/ _ \/ _` | | __| '_ \  | |_) | '__/ _ \| '_ \ / _ \      |
#   |     |  _  |  __/ (_| | | |_| | | | |  __/| | | (_) | |_) |  __/      |
#   |     |_| |_|\___|\__,_|_|\__|_| |_| |_|   |_|  \___/|_.__/ \___|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_virtual_network_gateway_health(item: str, section: Section) -> CheckResult:
    if (vn_gateway := section.get(item)) is None:
        return

    health = vn_gateway.health
    health_available = health.availabilityState == "Available"

    yield Result(state=State.OK, summary=f"Availability state: {health.availabilityState}")
    yield Result(state=State.OK, summary=f"Summary: {health.summary}")

    if not health_available:
        occurred_time = parse_azure_datetime(health.occuredTime).timestamp()
        summary = (
            f"Reason type: {health.reasonType}, Occurred time: {render.datetime(occurred_time)}"
        )

        yield Result(state=State.CRIT, summary=summary)


check_plugin_azure_virtual_network_gateway_health = CheckPlugin(
    name="azure_virtual_network_gateway_health",
    sections=["azure_virtualnetworkgateways"],
    service_name="VNet Gateway %s Health Probe",
    discovery_function=discover_virtual_network_gateway,
    check_function=check_virtual_network_gateway_health,
)


#   .--BGP-----------------------------------------------------------------.
#   |                          ____   ____ ____                            |
#   |                         | __ ) / ___|  _ \                           |
#   |                         |  _ \| |  _| |_) |                          |
#   |                         | |_) | |_| |  __/                           |
#   |                         |____/ \____|_|                              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def get_peering_address_summary(bgp_settings: BgpSettings) -> Iterable[str]:
    peering_addresses: dict[str, list[str]] = defaultdict(list)

    for addresses in bgp_settings.bgpPeeringAddresses:
        peering_addresses["Default peering addresses"].extend(addresses.defaultBgpIpAddresses)
        peering_addresses["Custom peering addresses"].extend(addresses.customBgpIpAddresses)
        peering_addresses["Tunnel peering addresses"].extend(addresses.tunnelIpAddresses)

    for address_type, address_list in peering_addresses.items():
        yield f"{address_type}: {str(address_list)}"


def check_virtual_network_gateway_bgp(item: str, section: Section) -> CheckResult:
    if (vn_gateway := section.get(item)) is None:
        return

    settings = vn_gateway.settings
    bgp_settings = vn_gateway.settings.bgpSettings

    if settings.enableBgp and bgp_settings:
        yield Result(
            state=State.OK,
            summary=f"Enabled: {settings.enableBgp}, ASN: {bgp_settings.asn}, Peer weight: {bgp_settings.peerWeight}",
        )
        for summary in get_peering_address_summary(bgp_settings):
            yield Result(state=State.OK, summary=summary)
    else:
        yield Result(state=State.OK, summary=f"Enabled: {settings.enableBgp}")


check_plugin_azure_virtual_network_gateway_bgp = CheckPlugin(
    name="azure_virtual_network_gateway_bgp",
    sections=["azure_virtualnetworkgateways"],
    service_name="VNet Gateway %s BGP",
    discovery_function=discover_virtual_network_gateway,
    check_function=check_virtual_network_gateway_bgp,
)


#   .--Remote Peering------------------------------------------------------.
#   |                  ____                      _                         |
#   |                 |  _ \ ___ _ __ ___   ___ | |_ ___                   |
#   |                 | |_) / _ \ '_ ` _ \ / _ \| __/ _ \                  |
#   |                 |  _ <  __/ | | | | | (_) | ||  __/                  |
#   |                 |_| \_\___|_| |_| |_|\___/ \__\___|                  |
#   |                                                                      |
#   |                  ____                _                               |
#   |                 |  _ \ ___  ___ _ __(_)_ __   __ _                   |
#   |                 | |_) / _ \/ _ \ '__| | '_ \ / _` |                  |
#   |                 |  __/  __/  __/ |  | | | | | (_| |                  |
#   |                 |_|   \___|\___|_|  |_|_| |_|\__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+


def discover_virtual_network_gateway_peering(section: Section) -> DiscoveryResult:
    for item, vnet_gateway in section.items():
        for peering in vnet_gateway.remote_vnet_peerings:
            yield Service(
                item=f"{item} Remote Peering {peering.name}",
                labels=get_service_labels_from_resource_tags(vnet_gateway.resource.tags),
            )


def check_virtual_network_gateway_peering(item: str, section: Section) -> CheckResult:
    vn_gateway_name, _, _, peering_name = item.split()
    if (vn_gateway := section.get(vn_gateway_name)) is None:
        return

    for peering in vn_gateway.remote_vnet_peerings:
        if peering.name == peering_name:
            peering_connected = (
                peering.peeringSyncLevel == "FullyInSync" and peering.peeringState == "Connected"
            )
            yield Result(
                state=State.OK if peering_connected else State.WARN,
                summary=f"Peering state: {peering.peeringState}, Peering sync level: {peering.peeringSyncLevel}",
            )


check_plugin_azure_virtual_network_gateway_peering = CheckPlugin(
    name="azure_virtual_network_gateway_peering",
    sections=["azure_virtualnetworkgateways"],
    service_name="VNet Gateway %s",
    discovery_function=discover_virtual_network_gateway_peering,
    check_function=check_virtual_network_gateway_peering,
)
