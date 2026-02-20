#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

import json
from collections.abc import Mapping
from typing import TypedDict

from pydantic import BaseModel, Field

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

type Section = Mapping[str, MerakiVpnPeer | ThirdPartyVpnPeer]


class MerakiVpnPeer(BaseModel, frozen=True):
    network_id: str = Field(alias="networkId")
    network_name: str = Field(alias="networkName")
    reachability: str


class ThirdPartyVpnPeer(BaseModel, frozen=True):
    name: str
    public_ip: str = Field(alias="publicIp")
    reachability: str


class VpnStatus(BaseModel, frozen=True):
    meraki_vpn_peers: list[MerakiVpnPeer] = Field(alias="merakiVpnPeers")
    third_party_vpn_peers: list[ThirdPartyVpnPeer] = Field(alias="thirdPartyVpnPeers")

    def get_peers_by_name(self) -> Section:
        return {
            **{peer.network_name: peer for peer in self.meraki_vpn_peers},
            **{peer.name: peer for peer in self.third_party_vpn_peers},
        }


def parse_appliance_vpns(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            vpn_status = VpnStatus.model_validate(json.loads(payload)[0])
            return vpn_status.get_peers_by_name()
        case _:
            return {}


agent_section_cisco_meraki_org_appliance_vpns = AgentSection(
    name="cisco_meraki_org_appliance_vpns",
    parse_function=parse_appliance_vpns,
)


def discover_appliance_vpns(section: Section) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


class CheckParams(TypedDict):
    status_not_reachable: int


def check_appliance_vpns(item: str, params: CheckParams, section: Section) -> CheckResult:
    if (peer := section.get(item)) is None:
        return None

    yield Result(
        state=State.OK
        if peer.reachability.lower() == "reachable"
        else State(params["status_not_reachable"]),
        summary=f"Reachability: {peer.reachability}",
    )

    match peer:
        case MerakiVpnPeer():
            yield Result(state=State.OK, summary="Type: Meraki VPN peer")
            yield Result(state=State.OK, notice=f"Network ID: {peer.network_id}")
        case ThirdPartyVpnPeer():
            yield Result(state=State.OK, summary="Type: Third party VPN peer")
            yield Result(state=State.OK, notice=f"Public IP: {peer.public_ip}")


check_plugin_cisco_meraki_org_appliance_vpns = CheckPlugin(
    name="cisco_meraki_org_appliance_vpns",
    service_name="VPN peer %s",
    discovery_function=discover_appliance_vpns,
    check_function=check_appliance_vpns,
    check_ruleset_name="cisco_meraki_org_appliance_vpns",
    check_default_parameters=CheckParams(status_not_reachable=State.WARN.value),
)
