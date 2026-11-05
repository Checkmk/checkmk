#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.merging import merge_trees
from cmk.inventory.trees import ImmutableTable, ImmutableTree, SDKey, SDNodeName

from ._fixtures import inventory_store


def _is_filled(tree: ImmutableTree, kind: str, path: Sequence[str]) -> bool:
    node = tree.get_tree(tuple(SDNodeName(p) for p in path))
    match kind:
        case "attributes":
            return len(node.attributes) > 0
        case "table":
            return len(node.table) > 0
        case _:
            return bool(node)


@pytest.mark.parametrize(
    "tree_name, filled",
    [
        (
            HostName("tree_old_arrays"),
            [
                ("node", ["hardware"]),
                ("node", ["networking"]),
                ("attributes", ["hardware", "memory", "arrays", "0"]),
                ("table", ["hardware", "memory", "arrays", "0", "devices"]),
                ("table", ["hardware", "memory", "arrays", "1", "others"]),
            ],
        ),
        (
            HostName("tree_new_memory"),
            [
                ("node", ["hardware"]),
                ("node", ["networking"]),
                ("attributes", ["hardware", "memory"]),
            ],
        ),
        (
            HostName("tree_new_interfaces"),
            [
                ("node", ["hardware"]),
                ("node", ["networking"]),
                ("node", ["software"]),
                ("table", ["hardware", "components", "backplanes"]),
                ("table", ["hardware", "components", "chassis"]),
                ("table", ["hardware", "components", "containers"]),
                ("table", ["hardware", "components", "fans"]),
                ("table", ["hardware", "components", "modules"]),
                ("table", ["hardware", "components", "others"]),
                ("table", ["hardware", "components", "psus"]),
                ("table", ["hardware", "components", "sensors"]),
                ("attributes", ["hardware", "system"]),
                ("attributes", ["software", "applications", "check_mk", "cluster"]),
                ("attributes", ["software", "os"]),
            ],
        ),
    ],
)
def test_merged_tree_keeps_the_content_of_the_right_tree(
    tree_name: HostName, filled: Sequence[tuple[str, Sequence[str]]]
) -> None:
    inv_store = inventory_store()
    tree = merge_trees(
        inv_store.load_inventory_tree(host_name=HostName("tree_old_addresses")),
        inv_store.load_inventory_tree(host_name=tree_name),
    )
    assert [(kind, path) for kind, path in filled if not _is_filled(tree, kind, path)] == []


def test_merged_tree_contains_the_status_data_table() -> None:
    inv_store = inventory_store()
    table = (
        merge_trees(
            inv_store.load_inventory_tree(host_name=HostName("tree_inv")),
            inv_store.load_inventory_tree(host_name=HostName("tree_status")),
        )
        .get_tree((SDNodeName("foobar"),))
        .table
    )
    assert (len(table), len(table.rows)) == (19, 5)


def test_merge_with_empty_tables() -> None:
    assert merge_trees(ImmutableTree(), ImmutableTree()) == ImmutableTree()


def test_merge_with_empty_left_table() -> None:
    assert merge_trees(
        ImmutableTree(),
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
                },
            )
        ),
    ) == ImmutableTree(
        table=ImmutableTable(
            key_columns=[SDKey("key_column")],
            rows_by_ident={
                ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
            },
        )
    )


def test_merge_with_empty_right_table() -> None:
    assert merge_trees(
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
                },
            )
        ),
        ImmutableTree(),
    ) == ImmutableTree(
        table=ImmutableTable(
            key_columns=[SDKey("key_column")],
            rows_by_ident={
                ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
            },
        )
    )


def test_merge_joins_the_rows_of_the_same_ident() -> None:
    assert merge_trees(
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("left"): "Left"}
                },
            )
        ),
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("right"): "Right"}
                },
            )
        ),
    ).table.rows == [
        {SDKey("key_column"): "Key Column", SDKey("left"): "Left", SDKey("right"): "Right"}
    ]
