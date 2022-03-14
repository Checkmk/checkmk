#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable
from cmk.base.plugins.agent_based.inventory_k8s_ingress_info import inventory_k8s_ingress_info

from .utils_inventory import sort_inventory_result

DATA0 = [
    [
        """
    {
        "cluster-example-ingress": {
        "backends": [
          [
            "example.com/",
            "example-name",
            8888
          ]
        ],
        "hosts": {
          "example.com-tls": [
            "example.com"
          ]
        },
        "load_balancers": [
          {
            "hostname": "",
            "ip": "10.100.100.171"
          },
          {
            "hostname": "",
            "ip": "10.100.100.172"
          },
          {
            "hostname": "",
            "ip": "10.100.100.173"
          }
        ]
      }
    }
    """
    ]
]

RESULT0 = [
    TableRow(
        path=[
            "software",
            "applications",
            "kubernetes",
            "ingresses",
            "cluster-example-ingress",
            "backends",
        ],
        key_columns={"path": "example.com/", "service_name": "example-name", "service_port": 8888},
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=[
            "software",
            "applications",
            "kubernetes",
            "ingresses",
            "cluster-example-ingress",
            "hosts",
        ],
        key_columns={"host": "example.com", "secret_name": "example.com-tls"},
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=[
            "software",
            "applications",
            "kubernetes",
            "ingresses",
            "cluster-example-ingress",
            "load_balancers",
        ],
        key_columns={"hostname": "", "ip": "10.100.100.171"},
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=[
            "software",
            "applications",
            "kubernetes",
            "ingresses",
            "cluster-example-ingress",
            "load_balancers",
        ],
        key_columns={"hostname": "", "ip": "10.100.100.172"},
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=[
            "software",
            "applications",
            "kubernetes",
            "ingresses",
            "cluster-example-ingress",
            "load_balancers",
        ],
        key_columns={"hostname": "", "ip": "10.100.100.173"},
        inventory_columns={},
        status_columns={},
    ),
]


@pytest.mark.parametrize(
    "data, result",
    [
        (DATA0, RESULT0),
    ],
)
def test_inv_k8s_ingress_info(data: StringTable, result: InventoryResult):
    assert sort_inventory_result(
        inventory_k8s_ingress_info(json.loads(data[0][0]))
    ) == sort_inventory_result(result)
