#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawUplinkVpnStatuses(TypedDict):
    """
    Appliance Uplink VPN Statuses Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-appliance-vpn-statuses/>
    """

    networkId: str
    networkName: str
    deviceSerial: str
    deviceStatus: str
    uplinks: list[_Uplink]
    vpnMode: str
    exportedSubnets: list[_ExportedSubnet]
    merakiVpnPeers: list[_MerakiVpnPeer]
    thirdPartyVpnPeers: list[Third_PartyVpnPeer]


class _Uplink(TypedDict):
    interface: str
    publicIp: str


class _ExportedSubnet(TypedDict):
    subnet: str
    name: str


class _MerakiVpnPeer(TypedDict):
    networkId: str
    networkName: str
    reachability: str


class Third_PartyVpnPeer(TypedDict):
    name: str
    publicIp: str
    reachability: str
