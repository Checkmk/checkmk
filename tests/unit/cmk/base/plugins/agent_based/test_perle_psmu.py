#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.perle_psmu import inventory_perle_psmu, parse_perle_psmu

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                ["1", "MCR-ACPWR", "Foo", "104-101015T10175", "1", "12.05", "6.75", "1"],
                ["2", "MCR-ACPWR", "Bar", "104-101015T10177", "1", "12.05", "6.75", "1"],
            ],
            [
                TableRow(
                    path=["hardware", "components", "psus"],
                    key_columns={
                        "index": "1",
                    },
                    inventory_columns={
                        "description": "Foo",
                        "model": "MCR-ACPWR",
                        "serial": "104-101015T10175",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "components", "psus"],
                    key_columns={
                        "index": "2",
                    },
                    inventory_columns={
                        "description": "Bar",
                        "model": "MCR-ACPWR",
                        "serial": "104-101015T10177",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_perle_psmu(string_table, expected_result):
    assert sort_inventory_result(
        inventory_perle_psmu(parse_perle_psmu(string_table))
    ) == sort_inventory_result(expected_result)
