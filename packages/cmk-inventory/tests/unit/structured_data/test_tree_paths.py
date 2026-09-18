#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.inventory.structured_data import (
    InventoryPath,
    make_filter_choices_from_api_request_paths,
    parse_internal_raw_path,
    SDFilterChoice,
    SDKey,
    SDNodeName,
    TreeSource,
)


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


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        # Tuple format
        (
            ".path.to.node.",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:*.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
        (
            ".path.to.node.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
    ],
)
def test__make_filter_choices_from_api_request_paths(
    entry: str, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_api_request_paths([entry])[0] == expected_filter_choice
