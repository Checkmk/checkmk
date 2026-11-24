#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.delta import compare_trees

from ._fixtures import inventory_store


@pytest.mark.parametrize(
    "tree_name_old, tree_name_new, result",
    [
        (
            HostName("tree_old_addresses_arrays_memory"),
            HostName("tree_new_addresses_arrays_memory"),
            (3, 2, 1),
        ),
        (
            HostName("tree_old_addresses"),
            HostName("tree_new_addresses"),
            (5, 0, 6),
        ),
        (
            HostName("tree_old_arrays"),
            HostName("tree_new_arrays"),
            (2, 0, 2),
        ),
        (
            HostName("tree_old_interfaces"),
            HostName("tree_new_interfaces"),
            (17, 0, 116),
        ),
        (
            HostName("tree_old_memory"),
            HostName("tree_new_memory"),
            (1, 1, 1),
        ),
        (
            HostName("tree_old_heute"),
            HostName("tree_new_heute"),
            (1, 1, 2),
        ),
    ],
)
def test_compare_real_trees(
    tree_name_old: HostName, tree_name_new: HostName, result: tuple[int, int, int]
) -> None:
    inv_store = inventory_store()
    old_tree = inv_store.load_inventory_tree(host_name=tree_name_old)
    new_tree = inv_store.load_inventory_tree(host_name=tree_name_new)
    stats = compare_trees(new_tree, old_tree).get_stats()
    assert (stats["new"], stats["changed"], stats["removed"]) == result
