#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Iterable

from cmk.agent_based.v2 import Attributes, TableRow
from cmk.plugins.collection.agent_based.inventory_mobileiron import inventory_mobileiron
from cmk.plugins.collection.agent_based.mobileiron_section import parse_mobileiron

from .utils_inventory import sort_inventory_result

DEVICE_DATA = parse_mobileiron(
    [
        [
            json.dumps(
                {
                    "deviceModel": "asdf_model",
                    "platformType": "ANDROID",
                    "registrationState": "ACTIVE",
                    "manufacturer": "iasdf",
                    "serialNumber": "asdf",
                    "dmPartitionName": "ASDF_PARTITION",
                    "ipAddress": "10.10.10.10",
                }
            )
        ]
    ]
)


EXPECTED: Iterable[Attributes | TableRow] = [
    Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "model": "asdf_model",
            "manufacturer": "iasdf",
            "serial": "asdf",
        },
    ),
    Attributes(
        path=["software", "os"],
        inventory_attributes={
            "type": "ANDROID",
        },
    ),
    TableRow(
        path=["networking", "addresses"],
        key_columns={
            "address": "10.10.10.10",
            "device": "generic",
        },
        inventory_columns={
            "type": "ipv4",
        },
    ),
    Attributes(
        path=["software", "applications", "mobileiron"],
        inventory_attributes={
            "registration_state": "ACTIVE",
            "partition_name": "ASDF_PARTITION",
        },
    ),
]


def test_inventory_mobileiron() -> None:
    assert sort_inventory_result(inventory_mobileiron(DEVICE_DATA)) == sort_inventory_result(
        EXPECTED
    )
