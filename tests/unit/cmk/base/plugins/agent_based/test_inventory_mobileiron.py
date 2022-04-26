#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Iterable, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.inventory_mobileiron import inventory_mobileiron
from cmk.base.plugins.agent_based.utils.mobileiron import parse_mobileiron

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
                    "totalCapacity": 67.108864,
                    "dmPartitionName": "ASDF_PARTITION",
                    "ipAddress": "10.10.10.10",
                }
            )
        ]
    ]
)


EXPECTED: Iterable[Union[Attributes, TableRow]] = [
    Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "Model Name": "asdf_model",
            "Manufacturer": "iasdf",
            "Serial number": "asdf",
        },
    ),
    Attributes(
        path=["software", "os"],
        inventory_attributes={
            "Type": "ANDROID",
        },
    ),
    Attributes(
        path=["hardware", "storage", "disks"],
        inventory_attributes={"size": 72057594037.92793},
    ),
    Attributes(
        path=["networking", "addresses"],
        inventory_attributes={"address": "10.10.10.10"},
    ),
    Attributes(
        path=["software", "applications", "mobileiron"],
        inventory_attributes={
            "Registration state": "ACTIVE",
            "Partition name": "ASDF_PARTITION",
        },
    ),
]


def test_inventory_mobileiron() -> None:
    assert sort_inventory_result(inventory_mobileiron(DEVICE_DATA)) == sort_inventory_result(
        EXPECTED
    )
