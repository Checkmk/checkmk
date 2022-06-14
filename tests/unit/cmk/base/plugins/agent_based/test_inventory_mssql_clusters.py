#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_mssql_clusters import (
    inventory_mssql_clusters,
    parse_mssql_clusters,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "MSSQL_VIM_SQLEXP2",
                    "MyDB",
                    "node3",
                    "node3,node4",
                ],
                [
                    "MSSQL_VIM_SQLEXP",
                    "node1",
                    "node1,node2",
                ],
            ],
            [
                TableRow(
                    path=["software", "applications", "mssql", "instances"],
                    key_columns={
                        "name": "MSSQL_VIM_SQLEXP",
                    },
                    inventory_columns={
                        "active_node": "node1",
                        "node_names": "node1, node2",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "mssql", "instances"],
                    key_columns={
                        "name": "MSSQL_VIM_SQLEXP2",
                    },
                    inventory_columns={
                        "active_node": "node3",
                        "node_names": "node3, node4",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_mssql_clusters(string_table, expected_result) -> None:
    assert sort_inventory_result(
        inventory_mssql_clusters(parse_mssql_clusters(string_table))
    ) == sort_inventory_result(expected_result)
