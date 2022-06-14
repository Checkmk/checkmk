#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.ibm_mq_managers import inventory_ibm_mq_managers


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        ({}, []),
        (
            {
                "name1": {
                    "INSTVER": "instver",
                    "INSTNAME": "instname",
                    "HA": "ha",
                    "STANDBY": "standby",
                    "STATUS": "status",
                },
                "name2": {
                    "INSTVER": "instver",
                    "INSTNAME": "instname",
                    "STANDBY": "standby",
                    "STATUS": "status",
                },
            },
            [
                TableRow(
                    path=["software", "applications", "ibm_mq", "managers"],
                    key_columns={
                        "name": "name1",
                    },
                    inventory_columns={
                        "instver": "instver",
                        "instname": "instname",
                        "ha": "ha",
                    },
                    status_columns={
                        "standby": "standby",
                        "status": "status",
                    },
                ),
                TableRow(
                    path=["software", "applications", "ibm_mq", "managers"],
                    key_columns={
                        "name": "name2",
                    },
                    inventory_columns={
                        "instver": "instver",
                        "instname": "instname",
                        "ha": "n/a",
                    },
                    status_columns={
                        "standby": "standby",
                        "status": "status",
                    },
                ),
            ],
        ),
    ],
)
def test_inv_aix_baselevel(parsed, expected_result) -> None:
    assert list(inventory_ibm_mq_managers(parsed)) == expected_result
