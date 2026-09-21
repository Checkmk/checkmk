#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.merging import merge_trees
from cmk.inventory.serialization import serialize_tree
from cmk.inventory.structured_data import ImmutableTable, ImmutableTree, SDKey, SDNodeName

from ._fixtures import inventory_store


@pytest.mark.parametrize(
    "tree_name, edges, sub_children",
    [
        (
            HostName("tree_old_arrays"),
            ["hardware", "networking"],
            [
                ("get_attributes", ["hardware", "memory", "arrays", "0"]),
                ("get_table", ["hardware", "memory", "arrays", "0", "devices"]),
                ("get_table", ["hardware", "memory", "arrays", "1", "others"]),
            ],
        ),
        (
            HostName("tree_new_memory"),
            ["hardware", "networking"],
            [
                ("get_attributes", ["hardware", "memory"]),
            ],
        ),
        (
            HostName("tree_new_interfaces"),
            ["hardware", "networking", "software"],
            [
                ("get_table", ["hardware", "components", "backplanes"]),
                ("get_table", ["hardware", "components", "chassis"]),
                ("get_table", ["hardware", "components", "containers"]),
                ("get_table", ["hardware", "components", "fans"]),
                ("get_table", ["hardware", "components", "modules"]),
                ("get_table", ["hardware", "components", "others"]),
                ("get_table", ["hardware", "components", "psus"]),
                ("get_table", ["hardware", "components", "sensors"]),
                ("get_attributes", ["hardware", "system"]),
                ("get_attributes", ["software", "applications", "check_mk", "cluster"]),
                ("get_attributes", ["software", "os"]),
            ],
        ),
    ],
)
def test_merge_trees_1(
    tree_name: HostName, edges: Sequence[str], sub_children: Sequence[tuple[str, Sequence[str]]]
) -> None:
    inv_store = inventory_store()
    tree = merge_trees(
        inv_store.load_inventory_tree(host_name=HostName("tree_old_addresses")),
        inv_store.load_inventory_tree(host_name=tree_name),
    )

    for edge in edges:
        assert bool(tree.get_tree((SDNodeName(edge),)))

    for m_name, path in sub_children:
        node_names = tuple(SDNodeName(p) for p in path)
        if m_name == "get_attributes":
            assert len(tree.get_tree(node_names).attributes) > 0
        elif m_name == "get_table":
            assert len(tree.get_tree(node_names).table) > 0


def test_merge_trees_2() -> None:
    inv_store = inventory_store()
    inventory_tree = inv_store.load_inventory_tree(host_name=HostName("tree_inv"))
    status_data_tree = inv_store.load_inventory_tree(host_name=HostName("tree_status"))
    tree = merge_trees(inventory_tree, status_data_tree)
    assert "foobar" in serialize_tree(tree)["Nodes"]
    table = tree.get_tree((SDNodeName("foobar"),)).table
    assert len(table) == 19
    assert len(table.rows) == 5


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
