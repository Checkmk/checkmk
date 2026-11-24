#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.trees import SDNodeName

from ._fixtures import inventory_store


def test_real_tree_order() -> None:
    inv_store = inventory_store()
    tree_ordered = inv_store.load_inventory_tree(host_name=HostName("tree_addresses_ordered"))
    tree_unordered = inv_store.load_inventory_tree(host_name=HostName("tree_addresses_unordered"))
    assert tree_ordered == tree_unordered


@pytest.mark.parametrize(
    "tree_name, result",
    [
        (HostName("tree_old_addresses_arrays_memory"), 21),
        (HostName("tree_old_addresses"), 9),
        (HostName("tree_old_arrays"), 10),
        (HostName("tree_old_interfaces"), 6284),
        (HostName("tree_old_memory"), 2),
        (HostName("tree_old_heute"), 16654),
        (HostName("tree_new_addresses_arrays_memory"), 23),
        (HostName("tree_new_addresses"), 8),
        (HostName("tree_new_arrays"), 10),
        (HostName("tree_new_interfaces"), 6185),
        (HostName("tree_new_memory"), 2),
        (HostName("tree_new_heute"), 16653),
    ],
)
def test_a_real_tree_counts_its_entries(tree_name: HostName, result: int) -> None:
    assert len(inventory_store().load_inventory_tree(host_name=tree_name)) == result


@pytest.mark.parametrize(
    "tree_name, edges_t, edges_f",
    [
        (
            HostName("tree_old_addresses_arrays_memory"),
            ["hardware", "networking"],
            ["", "foobar", "software"],
        ),
        (
            HostName("tree_old_addresses"),
            ["networking"],
            ["", "foobar", "hardware", "software"],
        ),
        (
            HostName("tree_old_arrays"),
            ["hardware"],
            ["", "foobar", "software", "networking"],
        ),
        (
            HostName("tree_old_interfaces"),
            ["hardware", "software", "networking"],
            ["", "foobar"],
        ),
        (
            HostName("tree_old_memory"),
            ["hardware"],
            ["", "foobar", "software", "networking"],
        ),
        (
            HostName("tree_old_heute"),
            ["hardware", "software", "networking"],
            ["", "foobar"],
        ),
    ],
)
def test_a_real_tree_has_content_only_below_its_known_nodes(
    tree_name: HostName, edges_t: Iterable[SDNodeName], edges_f: Iterable[SDNodeName]
) -> None:
    tree = inventory_store().load_inventory_tree(host_name=tree_name)
    assert {e: len(tree.get_tree((e,))) > 0 for e in [*edges_t, *edges_f]} == {
        **dict.fromkeys(edges_t, True),
        **dict.fromkeys(edges_f, False),
    }
