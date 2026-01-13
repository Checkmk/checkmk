#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.network.agent_based.ifname import (
    IfNameEntry,
    inventorize_if_name,
    parse_if_name,
)

LIST_OF_IF_NAME_ENTRIES = [
    IfNameEntry(index=1, name="lo"),
    IfNameEntry(index=2, name="eth-idrc0"),
    IfNameEntry(index=3, name="eth1"),
    IfNameEntry(index=4, name="eth2"),
    IfNameEntry(index=5, name="eth3"),
    IfNameEntry(index=6, name="Mgmt"),
    IfNameEntry(index=7, name="bond1"),
    IfNameEntry(index=8, name="bond1.3000"),
    IfNameEntry(index=9, name="bond1.3001"),
]


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        (
            [
                ["1", "lo"],
                ["2", "eth-idrc0"],
                ["3", "eth1"],
                ["4", "eth2"],
                ["5", "eth3"],
                ["6", "Mgmt"],
                ["7", "bond1"],
                ["8", "bond1.3000"],
                ["9", "bond1.3001"],
            ],
            LIST_OF_IF_NAME_ENTRIES,
        ),
    ],
)
def test_parse_interface_name(
    string_table: StringTable, expected_section: list[IfNameEntry]
) -> None:
    assert parse_if_name(string_table) == expected_section


@pytest.mark.parametrize(
    "section, result",
    [
        (
            LIST_OF_IF_NAME_ENTRIES,
            [
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 1},
                    inventory_columns={"name": "lo"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 2},
                    inventory_columns={"name": "eth-idrc0"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 3},
                    inventory_columns={"name": "eth1"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 4},
                    inventory_columns={"name": "eth2"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 5},
                    inventory_columns={"name": "eth3"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 6},
                    inventory_columns={"name": "Mgmt"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 7},
                    inventory_columns={"name": "bond1"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 8},
                    inventory_columns={"name": "bond1.3000"},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={"index": 9},
                    inventory_columns={"name": "bond1.3001"},
                ),
            ],
        ),
    ],
)
def test_check_interface_name_result(
    section: list[IfNameEntry],
    result: InventoryResult,
) -> None:
    assert list(inventorize_if_name(section)) == result
