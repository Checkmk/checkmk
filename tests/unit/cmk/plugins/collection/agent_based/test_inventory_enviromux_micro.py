#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.inventory_enviromux_micro import (
    inventory_enviromux_micro_information,
    parse_enviromux_micro_information,
)

from .utils_inventory import sort_inventory_result

STRING_TABLE = [["test-name", "E-MICRO-T", "799", "3.20"]]


def test_inventory_enviromux_micro_information() -> None:
    assert sort_inventory_result(
        inventory_enviromux_micro_information(
            parse_enviromux_micro_information(STRING_TABLE),
        )
    ) == sort_inventory_result(
        [
            Attributes(
                path=["hardware", "system"],
                inventory_attributes={
                    "Description": "test-name",
                    "Model": "E-MICRO-T",
                    "Serial Number": "799",
                },
            ),
            Attributes(
                path=["software", "firmware"],
                inventory_attributes={
                    "Vendor": "NTI",
                    "Version": "3.20",
                },
            ),
        ]
    )


def test_inventory_enviromux_micro_information_no_input() -> None:
    assert sort_inventory_result(
        inventory_enviromux_micro_information(
            parse_enviromux_micro_information([]),
        )
    ) == sort_inventory_result([])
