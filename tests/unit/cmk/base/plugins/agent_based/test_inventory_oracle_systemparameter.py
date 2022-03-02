#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_oracle_systemparameter import (
    inventory_oracle_systemparameter,
    parse_oracle_systemparameter,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        ([["", "", ""]], []),
        (
            [
                [
                    "XE",
                    "lock_name_space",
                    "",
                    "TRUE",
                ],
                [
                    "XE",
                    "sessions",
                    "172",
                    "FALSE",
                ],
                [
                    "XE",
                    "processes",
                    "100",
                    "TRUE",
                ],
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "systemparameter"],
                    key_columns={
                        "sid": "XE",
                        "name": "lock_name_space",
                    },
                    inventory_columns={
                        "value": "",
                        "isdefault": "TRUE",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "oracle", "systemparameter"],
                    key_columns={
                        "sid": "XE",
                        "name": "processes",
                    },
                    inventory_columns={
                        "value": "100",
                        "isdefault": "TRUE",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "oracle", "systemparameter"],
                    key_columns={
                        "sid": "XE",
                        "name": "sessions",
                    },
                    inventory_columns={
                        "value": "172",
                        "isdefault": "FALSE",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_oracle_systemparameter(string_table, expected_result):
    assert sort_inventory_result(
        inventory_oracle_systemparameter(parse_oracle_systemparameter(string_table))
    ) == sort_inventory_result(expected_result)
