#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Attributes, InventoryResult, StringTable, TableRow
from cmk.plugins.collection.agent_based.inventory_aix_service_packs import (
    inventory_aix_service_packs,
    parse_aix_service_packs,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        (
            [],
            [
                Attributes(
                    path=["software", "os"],
                    inventory_attributes={"service_pack": None},
                ),
            ],
        ),
        (
            [
                ["----", "foo"],
                ["latest"],
                ["Known", "bar"],
                ["pack"],
            ],
            [
                Attributes(
                    path=["software", "os"],
                    inventory_attributes={"service_pack": "latest"},
                ),
                TableRow(
                    path=["software", "os", "service_packs"],
                    key_columns={"name": "pack"},
                ),
            ],
        ),
    ],
)
def test_inv_aix_baselevel(raw_section: StringTable, expected_result: InventoryResult) -> None:
    assert sort_inventory_result(
        inventory_aix_service_packs(parse_aix_service_packs(raw_section))
    ) == sort_inventory_result(expected_result)
