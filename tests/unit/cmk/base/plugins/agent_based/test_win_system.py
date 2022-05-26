#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            [
                ["Manufacturer ", " Dell Inc."],
                ["Name ", " System Enclosure"],
                ["HotSwappable ", ""],
                ["InstallDate ", ""],
                ["PartNumber ", ""],
                ["SerialNumber ", " 54P4MR2"],
                ["Model ", " PowerEdge R640"],
                ["Manufacturer ", " Dell Inc."],
                ["Name ", " System Enclosure"],
                ["HotSwappable ", ""],
                ["InstallDate ", ""],
                ["PartNumber ", ""],
                ["SerialNumber ", " 54P4MR2"],
                ["Model ", " PowerEdge R640"],
            ],
            Attributes(
                path=["hardware", "system"],
                inventory_attributes={
                    "manufacturer": "Dell Inc.",
                    "product": "System Enclosure",
                    "serial": "54P4MR2",
                    "family": "PowerEdge R640",
                },
                status_attributes={},
            ),
            id="physical_machine",
        ),
        pytest.param(
            [
                ["HotSwappable", ""],
                ["InstallDate", ""],
                ["Manufacturer", " Oracle Corporation"],
                ["Model", ""],
                ["Name", " System Enclosure"],
                ["PartNumber", ""],
                ["SerialNumber", ""],
            ],
            Attributes(
                path=["hardware", "system"],
                inventory_attributes={
                    "manufacturer": "Oracle Corporation",
                    "family": "",
                    "product": "System Enclosure",
                    "serial": "",
                },
                status_attributes={},
            ),
            id="virtual_machine",
        ),
    ],
)
def test_inventory(
    fix_register: FixRegister,
    string_table: StringTable,
    expected_result: Attributes,
) -> None:
    assert list(
        fix_register.inventory_plugins[InventoryPluginName("win_system")].inventory_function(
            string_table
        )
    ) == [expected_result]
