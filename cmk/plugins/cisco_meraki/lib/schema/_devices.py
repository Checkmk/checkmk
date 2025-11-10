#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawDevice(TypedDict):
    """
    Organization Devices Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-devices/>
    """

    name: str
    lat: float
    lng: float
    address: str
    notes: str
    tags: list[str]
    networkId: str
    serial: str
    model: str
    imei: str
    mac: str
    lanIp: str
    firmware: str
    productType: str
    details: list[_Detail]


class Device(RawDevice):
    """Wrapped version of Device Resource."""

    organisation_id: str
    organisation_name: str


class _Detail(TypedDict):
    name: str
    value: str
