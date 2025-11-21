#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawUplinkStatuses(TypedDict):
    """
    Appliance Uplink Statuses Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-appliance-uplink-statuses/>
    """

    networkId: str
    serial: str
    model: str
    lastReportedAt: str
    highAvailability: _HighAvailability
    uplinks: list[_Uplink]


class UplinkStatuses(RawUplinkStatuses):
    networkName: str
    usageByInterface: UplinkUsageByInterface


type UplinkUsageByInterface = dict[str, dict[str, int]]


class _HighAvailability(TypedDict):
    enabled: bool
    role: str


class _Uplink(TypedDict):
    interface: str
    status: str
    ip: str
    gateway: str
    publicIp: str
    primaryDns: str
    secondaryDns: str
    ipAssignedBy: str
