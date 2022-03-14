#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.ibm_mq_channels import inventory_ibm_mq_channels

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        ({}, []),
        (
            {
                "a1:b1": {
                    "CHLTYPE": "chltype",
                    "MONCHL": "monchl",
                    "STATUS": "status",
                },
                "a2:b2": {},
                "a3": {
                    "CHLTYPE": "chltype",
                    "MONCHL": "monchl",
                    "STATUS": "status",
                },
            },
            [
                TableRow(
                    path=["software", "applications", "ibm_mq", "channels"],
                    key_columns={
                        "qmgr": "a1",
                        "name": "b1",
                    },
                    inventory_columns={
                        "type": "chltype",
                        "monchl": "monchl",
                    },
                    status_columns={
                        "status": "status",
                    },
                ),
                TableRow(
                    path=["software", "applications", "ibm_mq", "channels"],
                    key_columns={
                        "qmgr": "a2",
                        "name": "b2",
                    },
                    inventory_columns={
                        "type": "Unknown",
                        "monchl": "n/a",
                    },
                    status_columns={
                        "status": "Unknown",
                    },
                ),
            ],
        ),
    ],
)
def test_inv_aix_baselevel(parsed, expected_result):
    assert sort_inventory_result(inventory_ibm_mq_channels(parsed)) == sort_inventory_result(
        expected_result
    )
