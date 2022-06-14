#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.k8s_nodes import inventory_k8s_nodes

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        ({}, []),
        (
            {
                "nodes": [
                    "node2",
                    "node1",
                ],
            },
            [
                TableRow(
                    path=["software", "applications", "kubernetes", "nodes"],
                    key_columns={
                        "id": "node1",
                    },
                    inventory_columns={},
                    status_columns={
                        "name": "node1",
                    },
                ),
                TableRow(
                    path=["software", "applications", "kubernetes", "nodes"],
                    key_columns={
                        "id": "node2",
                    },
                    inventory_columns={},
                    status_columns={
                        "name": "node2",
                    },
                ),
            ],
        ),
    ],
)
def test_k8s_nodes(parsed, expected_result) -> None:
    assert sort_inventory_result(inventory_k8s_nodes(parsed)) == sort_inventory_result(
        expected_result
    )
