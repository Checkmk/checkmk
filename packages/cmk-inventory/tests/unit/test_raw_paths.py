#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.inventory.raw_paths import InventoryPath, parse_internal_raw_path, TreeSource
from cmk.inventory.structured_data import SDKey, SDNodeName


@pytest.mark.parametrize(
    "raw_path, expected_path, expected_node_name",
    [
        (
            "",
            InventoryPath(
                path=(),
                source=TreeSource.node,
            ),
            "",
        ),
        (
            ".",
            InventoryPath(
                path=(),
                source=TreeSource.node,
            ),
            "",
        ),
        (
            ".hardware.",
            InventoryPath(
                path=(SDNodeName("hardware"),),
                source=TreeSource.node,
            ),
            "hardware",
        ),
        (
            ".hardware.cpu.",
            InventoryPath(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                source=TreeSource.node,
            ),
            "cpu",
        ),
        (
            ".hardware.cpu.model",
            InventoryPath(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                source=TreeSource.attributes,
                key=SDKey("model"),
            ),
            "cpu",
        ),
        (
            ".software.packages:",
            InventoryPath(
                path=(SDNodeName("software"), SDNodeName("packages")),
                source=TreeSource.table,
            ),
            "packages",
        ),
        (
            ".hardware.memory.arrays:*.",
            InventoryPath(
                (
                    SDNodeName("hardware"),
                    SDNodeName("memory"),
                    SDNodeName("arrays"),
                    SDNodeName("*"),
                ),
                source=TreeSource.node,
            ),
            "*",
        ),
        (
            ".software.packages:17.name",
            InventoryPath(
                path=(SDNodeName("software"), SDNodeName("packages")),
                source=TreeSource.table,
                key=SDKey("name"),
            ),
            "packages",
        ),
        (
            ".software.packages:*.name",
            InventoryPath(
                path=(SDNodeName("software"), SDNodeName("packages")),
                source=TreeSource.table,
                key=SDKey("name"),
            ),
            "packages",
        ),
        (
            ".hardware.memory.arrays:*.devices:*.speed",
            InventoryPath(
                path=(
                    SDNodeName("hardware"),
                    SDNodeName("memory"),
                    SDNodeName("arrays"),
                    SDNodeName("*"),
                    SDNodeName("devices"),
                ),
                source=TreeSource.table,
                key=SDKey("speed"),
            ),
            "devices",
        ),
        (
            ".path:*.to.node.key",
            InventoryPath(
                path=(SDNodeName("path"), SDNodeName("*"), SDNodeName("to"), SDNodeName("node")),
                source=TreeSource.attributes,
                key=SDKey("key"),
            ),
            "node",
        ),
    ],
)
def test_parse_tree_path(
    raw_path: str, expected_path: InventoryPath, expected_node_name: str
) -> None:
    inventory_path = parse_internal_raw_path(raw_path)
    assert inventory_path == expected_path
    assert inventory_path.node_name == expected_node_name
