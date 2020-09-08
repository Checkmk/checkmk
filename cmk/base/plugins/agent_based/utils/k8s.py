#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict, Dict, List


class Filesystem(TypedDict):
    capacity: int
    available: int
    inodes: int
    inodes_free: int


def to_filesystem(data: Dict[str, int]) -> Filesystem:
    return {
        "capacity": data["capacity"],
        "available": data["available"],
        "inodes": data["inodes"],
        "inodes_free": data["inodes_free"],
    }


class Interface(TypedDict):
    # Note: since used for Counters only float/int are allowed
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int
    rx_bytes: int
    tx_bytes: int
    rx_dropped: int
    tx_dropped: int


def to_interface(data: Dict[str, int]) -> Interface:
    return {
        "rx_packets": data["rx_packets"],
        "tx_packets": data["tx_packets"],
        "rx_errors": data["rx_errors"],
        "tx_errors": data["tx_errors"],
        "rx_bytes": data["rx_bytes"],
        "tx_bytes": data["tx_bytes"],
        "rx_dropped": data["rx_dropped"],
        "tx_dropped": data["tx_dropped"],
    }


class Section(TypedDict):
    filesystem: Dict[str, List[Filesystem]]
    interfaces: Dict[str, List[Interface]]
    timestamp: float
