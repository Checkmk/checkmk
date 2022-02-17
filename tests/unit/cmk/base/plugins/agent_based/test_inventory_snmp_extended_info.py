#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, HostLabel, TableRow
from cmk.base.plugins.agent_based.inventory_snmp_extended_info import (
    get_device_type_label,
    inventory_snmp_extended_info,
    parse_snmp_extended_info,
)

from .utils_inventory import sort_inventory_result


def test_inventory_snmp_extended_info_host_labels():
    section = parse_snmp_extended_info(
        [
            ["_", "fibrechannel switch", "_", "_", "_", "_", "_", "_", "_"],
            ["_", "_", "_", "_", "_", "_", "_", "_", "_"],
        ]
    )
    assert list(get_device_type_label(section)) == [
        HostLabel("cmk/device_type", "fcswitch"),
    ]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            # Only one parent
            [
                [
                    "child",
                    "description",
                    "0",
                    "1",
                    "name",
                    "software",
                    "serial",
                    "manufacturer",
                    "model",
                ],
            ],
            [
                Attributes(
                    path=["hardware", "system"],
                    inventory_attributes={
                        "serial": "serial",
                        "model": "model",
                    },
                    status_attributes={},
                ),
            ],
        ),
        (
            # Ignore ports ('10')
            [
                [
                    "child",
                    "description",
                    "parent",
                    "10",
                    "name",
                    "software",
                    "serial",
                    "manufacturer",
                    "model",
                ],
            ],
            [],
        ),
        (
            # Only children
            [
                [
                    "child1",
                    "description",
                    "1",
                    "1",
                    "name1",
                    "software",
                    "serial",
                    "manufacturer",
                    "model",
                ],
                [
                    "child2",
                    "description",
                    "2",
                    "1",
                    "name2",
                    "software",
                    "serial",
                    "manufacturer",
                    "model",
                ],
            ],
            [
                TableRow(
                    path=["hardware", "components", "others"],
                    key_columns={
                        "index": "child1",
                        "name": "name1",
                    },
                    inventory_columns={
                        "description": "description",
                        "software": "software",
                        "serial": "serial",
                        "manufacturer": "manufacturer",
                        "model": "model",
                        "location": "Missing in ENTITY table (1)",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "components", "others"],
                    key_columns={
                        "index": "child2",
                        "name": "name2",
                    },
                    inventory_columns={
                        "description": "description",
                        "software": "software",
                        "serial": "serial",
                        "manufacturer": "manufacturer",
                        "model": "model",
                        "location": "Missing in ENTITY table (2)",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_snmp_extended_info(string_table, expected_result):
    assert sort_inventory_result(
        inventory_snmp_extended_info(parse_snmp_extended_info(string_table))
    ) == sort_inventory_result(expected_result)
