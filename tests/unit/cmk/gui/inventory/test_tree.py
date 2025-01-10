#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from pytest import MonkeyPatch

import cmk.utils
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    deserialize_tree,
    ImmutableTree,
    SDFilterChoice,
    SDKey,
    SDNodeName,
)

import cmk.gui.inventory
from cmk.gui.inventory._tree import (
    InventoryPath,
    load_filtered_and_merged_tree,
    make_filter_choices_from_api_request_paths,
    make_filter_choices_from_permitted_paths,
    parse_inventory_path,
    TreeSource,
)
from cmk.gui.type_defs import Row
from cmk.gui.watolib.groups_io import PermittedPath


@pytest.mark.parametrize(
    "raw_path, expected_path, expected_node_name",
    [
        (
            "",
            InventoryPath(
                path=tuple(),
                source=TreeSource.node,
            ),
            "",
        ),
        (
            ".",
            InventoryPath(
                path=tuple(),
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
    inventory_path = parse_inventory_path(raw_path)
    assert inventory_path == expected_path
    assert inventory_path.node_name == expected_node_name


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        (
            {
                "visible_raw_path": "path.to.node",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": ("choices", ["node"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes=[SDNodeName("node")],
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns=[SDKey("key")],
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="nothing",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="nothing",
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="nothing",
                nodes="all",
            ),
        ),
    ],
)
def test_make_filter_choices_from_permitted_paths(
    entry: PermittedPath, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_permitted_paths([entry])[0] == expected_filter_choice


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


@pytest.mark.parametrize(
    "hostname, row, expected_tree",
    [
        (
            None,
            {},
            deserialize_tree({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            {},
            deserialize_tree({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            {"host_structured_status": b""},
            deserialize_tree({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            {"host_structured_status": b"{'deserialized': 'tree'}"},
            deserialize_tree({"deserialized": "tree"}),
        ),
    ],
)
def test_load_filtered_and_merged_tree(
    monkeypatch: MonkeyPatch,
    hostname: HostName | None,
    row: Row,
    expected_tree: ImmutableTree,
    request_context: None,
) -> None:
    monkeypatch.setattr(
        cmk.gui.inventory._tree,  # pylint: disable=protected-access
        "_load_tree_from_file",
        (
            lambda *args, **kw: (
                deserialize_tree({"loaded": "tree"})
                if kw["tree_type"] == "status_data"
                else ImmutableTree()
            )
        ),
    )
    row.update({"host_name": hostname})
    assert load_filtered_and_merged_tree(row) == expected_tree
