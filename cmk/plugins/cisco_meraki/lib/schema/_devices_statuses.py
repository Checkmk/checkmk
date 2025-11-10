#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawDevicesStatus(TypedDict):
    """
    Organization Device Statuses Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-devices-statuses/>
    """

    name: str
    serial: str
    mac: str
    publicIp: str
    networkId: str
    status: str
    lastReportedAt: str
    lanIp: str
    gateway: str
    ipType: str
    primaryDns: str
    secondaryDns: str
    productType: str
    components: _Components
    model: str
    tags: list[str]


class _Components(TypedDict):
    powerSupplies: list[_PowerSupply]


class _PowerSupply(TypedDict):
    slot: int
    serial: str
    model: str
    status: str
    poe: _Poe


class _Poe(TypedDict):
    unit: str
    maximum: int
