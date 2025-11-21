#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawUplinkUsage(TypedDict):
    """
    Appliance Uplink Usage Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-appliance-uplinks-usage-by-network/>
    """

    networkId: str
    name: str
    byUplink: list[_ByUplink]


class _ByUplink(TypedDict):
    serial: str
    interface: str
    sent: int
    received: int
