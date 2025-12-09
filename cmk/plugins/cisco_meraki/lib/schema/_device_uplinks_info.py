#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawDeviceUplinksAddress(TypedDict):
    """
    Organization Devices Uplinks Addresses Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-devices-uplinks-addresses-by-device/>
    """

    mac: str
    name: str
    network: _VlanOrNetwork
    productType: str
    serial: str
    tags: list[str]
    uplinks: list[_Uplink]


class _VlanOrNetwork(TypedDict):
    id: str


class _Uplink(TypedDict):
    interface: str
    addresses: list[_Address]


class _Address(TypedDict):
    protocol: str
    assignmentMode: str
    address: str
    gateway: str
    nameservers: _Nameservers
    public: _Public
    vlan: _VlanOrNetwork


class _Nameservers(TypedDict):
    addresses: list[str]


class _Public(TypedDict):
    address: str
