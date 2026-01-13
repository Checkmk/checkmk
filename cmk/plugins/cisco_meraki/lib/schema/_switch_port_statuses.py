#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawSwitchPortStatus(TypedDict):
    """
    Device Switch Port Status Resource
    <https://developer.cisco.com/meraki/api-v1/get-device-switch-ports-statuses/>
    """

    portId: int
    enabled: bool
    status: str
    isUplink: bool
    errors: list[str]
    warnings: list[str]
    speed: str
    duplex: str
    spanningTree: _SpanningTree
    poe: _Poe
    usageInKb: _TrafficInKbpsOrUsageInKb
    cdp: _Cdp
    lldp: _Lldp
    clientCount: int
    powerUsageInWh: float
    trafficInKbps: _TrafficInKbpsOrUsageInKb
    securePort: _SecurePort


class _SpanningTree(TypedDict):
    statuses: list[str]


class _Poe(TypedDict):
    isAllocated: bool


class _Cdp(TypedDict):
    systemName: str
    platform: str
    deviceId: str
    portId: str
    nativeVlan: int
    address: str
    managementAddress: str
    version: str
    vtpManagementDomain: str
    capabilities: str


class _Lldp(TypedDict):
    systemName: str
    systemDescription: str
    chassisId: str
    portId: str
    managementVlan: int
    portVlan: int
    managementAddress: str
    portDescription: str
    systemCapabilities: str


class _TrafficInKbpsOrUsageInKb(TypedDict):
    total: float
    sent: float
    recv: int


class _SecurePort(TypedDict):
    enabled: bool
    active: bool
    authenticationStatus: str
    configOverrides: _ConfigOverrides


class _ConfigOverrides(TypedDict):
    type: str
    vlan: int
    voiceVlan: int
    allowedVlans: str
