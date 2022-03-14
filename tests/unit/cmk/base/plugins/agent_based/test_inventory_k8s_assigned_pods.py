#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_k8s_assigned_pods import inventory_k8s_assigned_pods

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        ({}, []),
        (
            {
                "names": [
                    "name2",
                    "name1",
                ]
            },
            [
                TableRow(
                    path=["software", "applications", "kubernetes", "assigned_pods"],
                    key_columns={
                        "id": "name1",
                    },
                    inventory_columns={},
                    status_columns={
                        "name": "name1",
                    },
                ),
                TableRow(
                    path=["software", "applications", "kubernetes", "assigned_pods"],
                    key_columns={
                        "id": "name2",
                    },
                    inventory_columns={},
                    status_columns={
                        "name": "name2",
                    },
                ),
            ],
        ),
    ],
)
def test_inventory_k8s_assigned_pods(raw_section, expected_result):
    assert sort_inventory_result(inventory_k8s_assigned_pods(raw_section)) == sort_inventory_result(
        expected_result
    )
