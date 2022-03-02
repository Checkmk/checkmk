#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_solaris_addresses import (
    inventory_solaris_addresses,
    parse_solaris_addresses,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "lo0:",
                    "flags=2001000849",
                    "<UP,LOOPBACK,RUNNING,MULTICAST,IPv4,VIRTUAL>",
                    "mtu",
                    "8232",
                    "index",
                    "1",
                ],
                ["inet", "127.0.0.1", "netmask", "ff000000"],
                [
                    "ce0:",
                    "flags=1000843",
                    "<UP,BROADCAST,RUNNING,MULTICAST,IPv4>mtu",
                    "1500",
                    "index",
                    "3",
                ],
                ["inet", "192.168.84.253", "netmask", "ffffff00", "broadcast", "192.168.84.255"],
                ["ether", "0:3:ba:7:84:5e"],
                [
                    "bge0:",
                    "flags=1004843",
                    "<UP,BROADCAST,RUNNING,MULTICAST,DHCP,IPv4>mtu",
                    "1500",
                    "index",
                    "2",
                ],
                ["inet", "10.8.57.39", "netmask", "ffffff00", "broadcast", "10.8.57.255"],
                ["ether", "0:3:ba:29:fc:cc"],
            ],
            [
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 2,
                        "description": "bge0",
                        "alias": "bge0",
                    },
                    inventory_columns={
                        "speed": 0,
                        "phys_address": "0:3:ba:29:fc:cc",
                        "port_type": 6,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 3,
                        "description": "ce0",
                        "alias": "ce0",
                    },
                    inventory_columns={
                        "speed": 0,
                        "phys_address": "0:3:ba:7:84:5e",
                        "port_type": 6,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "device": "bge0",
                    },
                    inventory_columns={
                        "address": "10.8.57.39",
                        "type": "IPv4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "device": "ce0",
                    },
                    inventory_columns={
                        "address": "192.168.84.253",
                        "type": "IPv4",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "device": "lo0",
                    },
                    inventory_columns={
                        "address": "127.0.0.1",
                        "type": "IPv4",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_solaris_addresses(string_table, expected_result):
    assert sort_inventory_result(
        inventory_solaris_addresses(parse_solaris_addresses(string_table))
    ) == sort_inventory_result(expected_result)
