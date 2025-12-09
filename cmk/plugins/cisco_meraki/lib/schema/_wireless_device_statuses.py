#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawWirelessDeviceStatus(TypedDict):
    """
    Wireless Device Status
    <https://developer.cisco.com/meraki/api-v1/get-device-wireless-status/>
    """

    basicServiceSets: list[_BasicServiceSet]


class _BasicServiceSet(TypedDict):
    ssidName: str
    ssidNumber: int
    enabled: bool
    band: str
    bssid: str
    channel: int
    channelWidth: str
    power: str
    visible: bool
    broadcasting: bool
