#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_solaris_routes import (
    inventory_solaris_routes,
    parse_solaris_routes,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["Routing", "Table:", "IPv4"],
                ["Destination", "Gateway", "Flags", "Ref", "Use", "Interface"],
                [
                    "--------------------",
                    "--------------------",
                    "-----",
                    "-----",
                    "----------",
                    "---------",
                ],
                ["default", "1.2.3.4", "UG", "1", "12"],
                ["default", "1.2.3.5", "UG", "1", "38", "aggr2320001"],
                ["1.2.30.0", "1.2.30.6", "U", "1", "160", "aggr3"],
                ["1.2.31.0", "1.2.31.7", "U", "1", "5", "aggr2"],
                ["1.0.0.0", "1.2.3.8", "U", "1", "0", "aggr3"],
                ["127.0.0.1", "127.0.0.1", "UH", "8", "46274", "lo0"],
            ],
            [
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "0.0.0.0/0",
                        "gateway": "1.2.3.4",
                    },
                    inventory_columns={
                        "device": None,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "0.0.0.0/0",
                        "gateway": "1.2.3.5",
                    },
                    inventory_columns={
                        "device": "aggr2320001",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "1.0.0.0",
                        "gateway": "1.2.3.8",
                    },
                    inventory_columns={
                        "device": "aggr3",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "1.2.30.0",
                        "gateway": "1.2.30.6",
                    },
                    inventory_columns={
                        "device": "aggr3",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "1.2.31.0",
                        "gateway": "1.2.31.7",
                    },
                    inventory_columns={
                        "device": "aggr2",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "routes"],
                    key_columns={
                        "target": "127.0.0.1",
                        "gateway": "127.0.0.1",
                    },
                    inventory_columns={
                        "device": "lo0",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_solaris_routes(string_table, expected_result) -> None:
    assert sort_inventory_result(
        inventory_solaris_routes(parse_solaris_routes(string_table))
    ) == sort_inventory_result(expected_result)
