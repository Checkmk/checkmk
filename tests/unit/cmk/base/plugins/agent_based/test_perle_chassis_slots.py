#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.perle_chassis_slots import inventory_perle_chassis_slots

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "1",
                    "PerleMC01",
                    "Foo",
                    "101-693515M10019",
                    "01.01.0004",
                    "1.8.G4",
                    "0",
                    "0",
                    "-2",
                    "Foo2",
                ],
                [
                    "2",
                    "CM-1000-SFP",
                    "Bar",
                    "102-094710M10033",
                    "1.1",
                    "1.2G1",
                    "0",
                    "0",
                    "1",
                    "Bar2",
                ],
            ],
            [
                TableRow(
                    path=["hardware", "components", "modules"],
                    key_columns={
                        "index": "1",
                        "name": "PerleMC01",
                    },
                    inventory_columns={
                        "description": "Foo2",
                        "model": "Foo",
                        "serial": "101-693515M10019",
                        "bootloader": "01.01.0004",
                        "firmware": "1.8.G4",
                        "type": "mcrMgt",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "components", "modules"],
                    key_columns={
                        "index": "2",
                        "name": "CM-1000-SFP",
                    },
                    inventory_columns={
                        "description": "Bar2",
                        "model": "Bar",
                        "serial": "102-094710M10033",
                        "bootloader": "1.1",
                        "firmware": "1.2G1",
                        "type": "cm1000Fixed",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_perle_chassis_slots(string_table, expected_result):
    assert sort_inventory_result(
        inventory_perle_chassis_slots(string_table)
    ) == sort_inventory_result(expected_result)
