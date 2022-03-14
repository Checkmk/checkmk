#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_win_ip_r import inventory_win_ip_r, parse_win_ip_r

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["indirect", "0.0.0.0", "0.0.0.0", "11.112.81.1", "vmxnet3 Ethernet Adapter #2"],
                [
                    "direct",
                    "11.112.81.0",
                    "255.255.255.0",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.34",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.36",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.39",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.41",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.43",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.44",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.45",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.46",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "11.112.81.255",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                ["direct", "11.112.136.0", "255.255.252.0", "0.0.0.0", "vmxnet3 Ethernet Adapter"],
                [
                    "direct",
                    "11.112.136.112",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter",
                ],
                [
                    "direct",
                    "11.112.139.255",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter",
                ],
                [
                    "direct",
                    "169.254.0.0",
                    "255.255.0.0",
                    "0.0.0.0",
                    "Microsoft Failover Cluster Virtual Adapter",
                ],
                [
                    "direct",
                    "169.254.2.184",
                    "255.255.255.255",
                    "0.0.0.0",
                    "Microsoft Failover Cluster Virtual Adapter",
                ],
                [
                    "direct",
                    "169.254.255.255",
                    "255.255.255.255",
                    "0.0.0.0",
                    "Microsoft Failover Cluster Virtual Adapter",
                ],
                ["direct", "224.0.0.0", "240.0.0.0", "0.0.0.0", "vmxnet3 Ethernet Adapter #2"],
                ["direct", "224.0.0.0", "240.0.0.0", "0.0.0.0", "vmxnet3 Ethernet Adapter"],
                [
                    "direct",
                    "224.0.0.0",
                    "240.0.0.0",
                    "0.0.0.0",
                    "Microsoft Failover Cluster Virtual Adapter",
                ],
                [
                    "direct",
                    "255.255.255.255",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter #2",
                ],
                [
                    "direct",
                    "255.255.255.255",
                    "255.255.255.255",
                    "0.0.0.0",
                    "vmxnet3 Ethernet Adapter",
                ],
                [
                    "direct",
                    "255.255.255.255",
                    "255.255.255.255",
                    "0.0.0.0",
                    "Microsoft Failover Cluster Virtual Adapter",
                ],
            ],
            [
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "0.0.0.0/0",
                        "gateway": "11.112.81.1",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "indirect",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.0/24",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.34/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.36/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.39/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.41/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.43/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.44/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.45/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.46/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.81.255/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.136.0/22",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.136.112/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "11.112.139.255/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "169.254.0.0/16",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "Microsoft Failover Cluster Virtual Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "169.254.2.184/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "Microsoft Failover Cluster Virtual Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "169.254.255.255/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "Microsoft Failover Cluster Virtual Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "224.0.0.0/4",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "224.0.0.0/4",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "224.0.0.0/4",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "Microsoft Failover Cluster Virtual Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "255.255.255.255/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter #2",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "255.255.255.255/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "vmxnet3 Ethernet Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "255.255.255.255/32",
                        "gateway": "0.0.0.0",
                    },
                    inventory_columns={
                        "device": "Microsoft Failover Cluster Virtual Adapter",
                        "type": "direct",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_win_ip_r(string_table, expected_result):
    assert sort_inventory_result(
        inventory_win_ip_r(parse_win_ip_r(string_table))
    ) == sort_inventory_result(expected_result)
