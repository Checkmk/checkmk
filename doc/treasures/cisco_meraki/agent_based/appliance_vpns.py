#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-04
# File  : appliance_vpns.py (check plugin)

# 2024-04-27: made data parsing more robust
# 2024-05-15: moved parse function to data classes
# 2024-06-29: refactored for CMK 2.3
#             changed service name from "Appliance VPN" to "VPN peer"
# 2024-06-30: renamed from cisco_meraki_org_appliance_vpns.py in to appliance_vpns.py

from abc import abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

from cmk_addons.plugins.meraki.lib.utils import load_json

# sample string_table
__appliance_vpn_statuses = [
    {
        'deviceSerial': 'ABCD-EFGH-RSTE',
        'deviceStatus': 'online',
        'exportedSubnets': [
            {
                'name': 'Management',
                'subnet': '172.18.10.0/24'
            },
            {
                'name': 'Clients',
                'subnet': '172.18.15.0/24'
            },
            {
                'name': 'WLAN',
                'subnet': '172.18.20.0/24'
            },
            {
                'name': 'Print',
                'subnet': '172.18.30.0/24'
            },
            {
                'name': 'VoIP',
                'subnet': '172.18.35.0/24'
            }
        ],
        'merakiVpnPeers': [
            {
                'networkId': 'L_5758978023500071234',
                'networkName': 'Networkname1',
                'reachability': 'reachable'
            },
            {
                'networkId': 'N_575897802350071601',
                'networkName': 'Networkname2',
                'reachability': 'reachable'
            }
        ],
        'networkId': 'L_5758978023500131234',
        'networkName': 'Networkname1',
        'serial': 'ABCD-1234-ZXYR',
        'thirdPartyVpnPeers': [
            {
                'name': 'Site-to-Site',
                'publicIp': '1.1.2.3',
                'reachability': 'unreachable'
            }
        ],
        'uplinks': [
            {
                'interface': 'wan1',
                'publicIp': '3.4.5.6'
            }
        ],
        'vpnMode': 'hub'
    }
]


@dataclass(frozen=True)
class ApplianceVPNUplink:
    interface: str | None
    public_ip: str | None

    @classmethod
    def parse(cls, uplink: Mapping[str, object]):
        return cls(
            interface=str(uplink['interface']) if uplink.get('interface') is not None else None,
            public_ip=str(uplink['publicIp']) if uplink.get('publicIp') is not None else None,
        )


@dataclass(frozen=True)
class ApplianceVPNPeer:
    device_vpn_mode: str | None
    network_name: str | None
    public_ip: str | None
    reachability: str | None
    type: str | None
    uplinks: Sequence[ApplianceVPNUplink] | None

    @abstractmethod
    def parse(self, peer: Mapping[str, object], uplinks: Sequence[ApplianceVPNUplink], mode: str | None):
        raise NotImplementedError()


@dataclass(frozen=True)
class ApplianceVPNPeerMeraki(ApplianceVPNPeer):
    @classmethod
    def parse(cls, peer: Mapping[str, object], uplinks: Sequence[ApplianceVPNUplink], mode: str | None):
        return cls(
            device_vpn_mode=str(mode) if mode is not None else None,
            network_name=str(peer['networkName']) if peer.get('networkName') is not None else None,
            public_ip=None,
            reachability=str(peer['reachability']) if peer.get('reachability') is not None else None,
            type='Meraki VPN Peer',
            uplinks=uplinks,
        )


@dataclass(frozen=True)
class ApplianceVPNPeerThirdParty(ApplianceVPNPeer):
    @classmethod
    def parse(cls, peer: Mapping[str, object], uplinks: Sequence[ApplianceVPNUplink], mode: str | None):
        return cls(
            device_vpn_mode=str(mode) if mode is not None else None,
            network_name=str(peer['name']) if peer.get('name') is not None else None,
            public_ip=str(peer['publicIp']) if peer.get('publicIp') is not None else None,
            reachability=str(peer['reachability']) if peer.get('reachability') is not None else None,
            type='third party VPN Peer',
            uplinks=uplinks,
        )


def parse_appliance_vpns(string_table: StringTable) -> Mapping[str, ApplianceVPNPeer]:
    json_data = load_json(string_table)
    json_data = json_data[0]

    vpn_uplinks = [ApplianceVPNUplink.parse(uplink) for uplink in json_data.get('uplinks', [])]

    meraki_peers = {peer['networkName']: ApplianceVPNPeerMeraki.parse(
        peer, vpn_uplinks, json_data.get('vpnMode')) for peer in json_data.get('merakiVpnPeers', [])}

    third_party_peers = {
        peer['name']: ApplianceVPNPeerThirdParty.parse(
            peer, vpn_uplinks, json_data.get('vpnMode')) for peer in json_data.get('thirdPartyVpnPeers', [])}

    meraki_peers.update(third_party_peers)

    return meraki_peers


agent_section_cisco_meraki_org_appliance_vpns = AgentSection(
    name="cisco_meraki_org_appliance_vpns",
    parse_function=parse_appliance_vpns,
)


def discover_appliance_vpns(section: Mapping[str, ApplianceVPNPeer]) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_appliance_vpns(item: str, params: Mapping[str, any], section: Mapping[str, ApplianceVPNPeer]) -> CheckResult:
    if (peer := section.get(item)) is None:
        return None

    if peer.reachability is not None and peer.reachability.lower() in ['reachable']:
        yield Result(state=State.OK, summary=f'Status: {peer.reachability}')
    else:
        yield Result(
            state=State(params.get('status_not_reachable', 1)),
            summary=f'Status: {peer.reachability}',
        )

    yield Result(state=State.OK, summary=f'Type: {peer.type}')
    if peer.public_ip:
        yield Result(state=State.OK, summary=f'Peer IP: {peer.public_ip}')

    yield Result(state=State.OK, notice=f'VPN Mode: {peer.device_vpn_mode}')
    yield Result(state=State.OK, notice=f'Uplink(s):')
    for uplink in peer.uplinks:
        yield Result(state=State.OK, notice=f'name: {uplink.interface}, public IP: {uplink.public_ip}')


check_plugin_cisco_meraki_org_appliance_vpns = CheckPlugin(
    name='cisco_meraki_org_appliance_vpns',
    service_name='VPN peer %s',
    discovery_function=discover_appliance_vpns,
    check_function=check_appliance_vpns,
    check_default_parameters={},
    check_ruleset_name='cisco_meraki_org_appliance_vpns',
)
