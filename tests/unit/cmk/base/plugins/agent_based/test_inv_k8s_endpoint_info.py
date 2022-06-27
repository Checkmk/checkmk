#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable
from cmk.base.plugins.agent_based.inventory_k8s_endpoint_info import inventory_k8s_endpoints
from cmk.base.plugins.agent_based.k8s_endpoint_info import parse_k8s_endpoint_info

from .utils_inventory import sort_inventory_result

DATA0 = [
    [
        """{
      "subsets": [
        {
          "addresses": [
            {
              "hostname": "",
              "ip": "10.100.100.179",
              "node_name": ""
            }
          ],
          "not_ready_addresses": [],
          "ports": [
            {
              "name": "https",
              "port": 6443,
              "protocol": "TCP"
            }
          ]
        }
      ]
    }"""
    ]
]

RESULT0 = [
    TableRow(
        path=["software", "applications", "kubernetes", "endpoints"],
        key_columns={
            "port": 6443,
            "port_name": "https",
            "protocol": "TCP",
            "hostname": "",
            "ip": "10.100.100.179",
        },
        inventory_columns={},
        status_columns={},
    )
]

DATA1 = [
    [
        """
    {
      "subsets": [
        {
          "addresses": [
            {
              "hostname": "",
              "ip": "10.100.100.171",
              "node_name": "worker03"
            },
            {
              "hostname": "",
              "ip": "10.100.100.172",
              "node_name": "worker02"
            },
            {
              "hostname": "",
              "ip": "10.100.100.173",
              "node_name": "worker01"
            },
            {
              "hostname": "",
              "ip": "10.100.100.179",
              "node_name": "master01"
            }
          ],
          "not_ready_addresses": [],
          "ports": [
            {
              "name": "https",
              "port": 9100,
              "protocol": "TCP"
            }
          ]
        }
      ]
    }
    """
    ]
]

RESULT1 = [
    TableRow(
        path=["software", "applications", "kubernetes", "endpoints"],
        key_columns={
            "port": 9100,
            "port_name": "https",
            "protocol": "TCP",
            "hostname": "",
            "ip": "10.100.100.171",
            "node_name": "worker03",
        },
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=["software", "applications", "kubernetes", "endpoints"],
        key_columns={
            "port": 9100,
            "port_name": "https",
            "protocol": "TCP",
            "hostname": "",
            "ip": "10.100.100.172",
            "node_name": "worker02",
        },
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=["software", "applications", "kubernetes", "endpoints"],
        key_columns={
            "port": 9100,
            "port_name": "https",
            "protocol": "TCP",
            "hostname": "",
            "ip": "10.100.100.173",
            "node_name": "worker01",
        },
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=["software", "applications", "kubernetes", "endpoints"],
        key_columns={
            "port": 9100,
            "port_name": "https",
            "protocol": "TCP",
            "hostname": "",
            "ip": "10.100.100.179",
            "node_name": "master01",
        },
        inventory_columns={},
        status_columns={},
    ),
]


@pytest.mark.parametrize(
    "data, result",
    [
        (DATA0, RESULT0),
        (DATA1, RESULT1),
    ],
)
def test_inv_k8s_endpoint_info(data: StringTable, result: InventoryResult) -> None:
    assert sort_inventory_result(
        inventory_k8s_endpoints(parse_k8s_endpoint_info(data))
    ) == sort_inventory_result(result)
