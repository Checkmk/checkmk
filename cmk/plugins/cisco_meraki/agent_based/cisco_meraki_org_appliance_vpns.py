#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import dataclasses
import json
from collections.abc import Mapping
from typing import TypedDict

from pydantic import BaseModel, computed_field, Field

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


@dataclasses.dataclass
class PeerInfo:
    reachability: str | None = None
    public_ip: str | None = None
    type: str | None = None

    def __post_init__(self) -> None:
        self.reachability = self.reachability or "n/a"
        self.public_ip = self.public_ip or "n/a"
        self.type = self.type or "n/a"

    @property
    def status_reachable(self) -> bool:
        if not self.reachability:
            return False
        return self.reachability.lower() == "reachable"


class Uplink(BaseModel, frozen=True):
    interface: str
    public_ip: str = Field(alias="publicIp")


class MerakiVpnPeer(BaseModel, frozen=True):
    network_name: str = Field(alias="networkName")
    reachability: str


class ThirdPartyVpnPeer(BaseModel, frozen=True):
    name: str
    public_ip: str = Field(alias="publicIp")
    reachability: str


class VpnStatus(BaseModel, frozen=True):
    meraki_vpn_peers_list: list[MerakiVpnPeer] = Field(alias="merakiVpnPeers")
    network_name: str = Field(alias="networkName")
    third_party_vpn_peers_list: list[ThirdPartyVpnPeer] = Field(alias="thirdPartyVpnPeers")
    uplinks: list[Uplink]
    vpn_mode: str = Field(alias="vpnMode")

    @computed_field
    @property
    def meraki_vpn_peers(self) -> dict[str, MerakiVpnPeer]:
        return {peer.network_name: peer for peer in self.meraki_vpn_peers_list}

    @computed_field
    @property
    def third_party_vpn_peers(self) -> dict[str, ThirdPartyVpnPeer]:
        return {peer.name: peer for peer in self.third_party_vpn_peers_list}

    @computed_field
    @property
    def info(self) -> PeerInfo:
        if meraki_peer := self.meraki_vpn_peers.get(self.network_name):
            return PeerInfo(
                public_ip=None,
                reachability=meraki_peer.reachability,
                type="Meraki VPN peer",
            )
        if third_party_peer := self.third_party_vpn_peers.get(self.network_name):
            return PeerInfo(
                public_ip=third_party_peer.public_ip,
                reachability=third_party_peer.reachability,
                type="Third party VPN peer",
            )
        return PeerInfo()


def parse_appliance_vpns(string_table: StringTable) -> dict[str, VpnStatus]:
    match string_table:
        case [[payload]] if payload:
            vpn_statuses = (VpnStatus.model_validate(data) for data in json.loads(payload))
            return {vpn.network_name: vpn for vpn in vpn_statuses}
        case _:
            return {}


agent_section_cisco_meraki_org_appliance_vpns = AgentSection(
    name="cisco_meraki_org_appliance_vpns",
    parse_function=parse_appliance_vpns,
)


def discover_appliance_vpns(section: Mapping[str, VpnStatus]) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


class CheckParams(TypedDict):
    status_not_reachable: int


def check_appliance_vpns(
    item: str, params: CheckParams, section: Mapping[str, VpnStatus]
) -> CheckResult:
    if (peer := section.get(item)) is None:
        return None

    if peer.info.status_reachable:
        yield Result(state=State.OK, summary=f"Status: {peer.info.reachability}")
    else:
        yield Result(
            state=State(params["status_not_reachable"]),
            summary=f"Status: {peer.info.reachability}",
        )

    yield Result(state=State.OK, summary=f"Type: {peer.info.type}")
    if peer.info.public_ip:
        yield Result(state=State.OK, summary=f"Peer IP: {peer.info.public_ip}")

    yield Result(state=State.OK, notice=f"VPN mode: {peer.vpn_mode}")
    yield Result(state=State.OK, notice="Uplink(s):")
    for uplink in peer.uplinks:
        yield Result(
            state=State.OK, notice=f"Name: {uplink.interface}, Public IP: {uplink.public_ip}"
        )


check_plugin_cisco_meraki_org_appliance_vpns = CheckPlugin(
    name="cisco_meraki_org_appliance_vpns",
    service_name="VPN peer %s",
    discovery_function=discover_appliance_vpns,
    check_function=check_appliance_vpns,
    check_ruleset_name="cisco_meraki_org_appliance_vpns",
    check_default_parameters=CheckParams(status_not_reachable=1),
)
