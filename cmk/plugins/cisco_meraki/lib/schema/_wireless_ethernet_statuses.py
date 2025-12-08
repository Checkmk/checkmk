#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawWirelessEthernetStatus(TypedDict):
    """
    Wireless Device Ethernet Status
    <https://developer.cisco.com/meraki/api-v1/get-organization-wireless-devices-ethernet-statuses/>
    """

    serial: str
    name: str
    network: _Network
    power: _Power
    ports: list[_Port]
    aggregation: _Aggregation


class _Network(TypedDict):
    id: str


class _Power(TypedDict):
    mode: str
    ac: _PoeOrAc
    poe: _PoeOrAc


class _PoeOrAc(TypedDict):
    isConnected: bool


class _Port(TypedDict):
    name: str
    poe: _Poe
    linkNegotiation: _LinkNegotiation


class _Poe(TypedDict):
    standard: str


class _LinkNegotiation(TypedDict):
    duplex: str
    speed: int


class _Aggregation(TypedDict):
    enabled: bool
    speed: int
