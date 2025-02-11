#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Attributes, InventoryResult, StringTable, TableRow
from cmk.plugins.collection.agent_based.inventory_dmidecode import (
    inventory_dmidecode,
    parse_dmidecode,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [
                ["BIOS Information"],
                ["", "Vendor", "Foo"],
                ["", "Version", "V1.15"],
                ["", "Release Date", "a-date"],
                ["", "BIOS Revision", "1.0"],
                ["", "Firmware Revision", "2.0"],
            ],
            [
                Attributes(
                    path=["software", "bios"],
                    inventory_attributes={
                        "vendor": "Foo",
                        "version": "V1.15",
                        "date": None,
                        "revision": "1.0",
                        "firmware": "2.0",
                    },
                )
            ],
            id="bios-information",
        ),
        pytest.param(
            [
                ["System Information"],
                ["", "Manufacturer", "Foo"],
                ["", "Product Name", "Bar"],
                ["", "Version", "V1.15"],
                ["", "Serial Number", "123"],
                ["", "UUID", "456"],
                ["", "Family", "Baz"],
            ],
            [
                Attributes(
                    path=["hardware", "system"],
                    inventory_attributes={
                        "manufacturer": "Foo",
                        "product": "Bar",
                        "version": "V1.15",
                        "serial": "123",
                        "uuid": "456",
                        "family": "Baz",
                    },
                )
            ],
            id="system-information",
        ),
        pytest.param(
            [
                ["Chassis Information"],
                ["", "Manufacturer", "Foo"],
                ["", "Type", "Bar"],
            ],
            [
                Attributes(
                    path=["hardware", "chassis"],
                    inventory_attributes={
                        "manufacturer": "Foo",
                        "type": "Bar",
                    },
                )
            ],
            id="chassis-information",
        ),
        pytest.param(
            [
                ["Processor Information"],
                ["", "Manufacturer", "Foo"],
                ["", "Max Speed", "1 Hz"],
                ["", "Voltage", "2"],
                ["", "Status", "Bar"],
            ],
            [
                Attributes(
                    path=["hardware", "cpu"],
                    inventory_attributes={
                        "vendor": "Foo",
                        "max_speed": 1.0,
                        "voltage": 2.0,
                        "status": "Bar",
                    },
                )
            ],
            id="processor-information",
        ),
        pytest.param(
            [
                ["Physical Memory Array"],
                ["", "Location", "Foo"],
                ["", "Use", "Bar"],
                ["", "Error Correction Type", "Baz"],
                ["", "Maximum Capacity", "1 b"],
                ["Memory Device"],
                ["", "Total Width", "1"],
                ["", "Data Width", "2"],
                ["", "Form Factor", "FF"],
                ["", "Set", "S"],
                ["", "Locator", "L"],
                ["", "Bank Locator", "BL"],
                ["", "Type", "T"],
                ["", "Type Detail", "TP"],
                ["", "Manufacturer", "M"],
                ["", "Serial Number", "123"],
                ["", "Asset Tag", "AT"],
                ["", "Part Number", "PN"],
                ["", "Speed", "3 Hz"],
                ["", "Size", "4 b"],
            ],
            [
                Attributes(
                    path=["hardware", "memory", "arrays", "1"],
                    inventory_attributes={
                        "location": "Foo",
                        "use": "Bar",
                        "error_correction": "Baz",
                        "maximum_capacity": 1,
                    },
                ),
                TableRow(
                    path=["hardware", "memory", "arrays", "1", "devices"],
                    key_columns={"index": 1, "set": "S"},
                    inventory_columns={
                        "total_width": "1",
                        "data_width": "2",
                        "form_factor": "FF",
                        "locator": "L",
                        "bank_locator": "BL",
                        "type": "T",
                        "type_detail": "TP",
                        "manufacturer": "M",
                        "serial": "123",
                        "asset_tag": "AT",
                        "part_number": "PN",
                        "speed": 3,
                        "size": 4,
                    },
                ),
            ],
            id="memory-array-devices",
        ),
    ],
)
def test_inventory_dmidecode(string_table: StringTable, expected_result: InventoryResult) -> None:
    assert list(inventory_dmidecode(parse_dmidecode(string_table))) == expected_result
