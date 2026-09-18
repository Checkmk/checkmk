#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.type_defs import Row
from cmk.gui.views.inventory._painters import _get_delta_tree, _get_inventory_tree
from cmk.inventory.structured_data import (
    deserialize_tree,
    ImmutableDeltaTree,
    ImmutableTree,
    SDKey,
)


def _tree() -> ImmutableTree:
    return deserialize_tree({"Attributes": {"Pairs": {SDKey("key"): "value"}}})


def test_get_inventory_tree_reads_the_column() -> None:
    assert _get_inventory_tree(Row({"host_inventory": _tree()})) == _tree()


def test_get_inventory_tree_without_the_column() -> None:
    assert _get_inventory_tree(Row({})) == ImmutableTree()


def test_get_inventory_tree_of_an_unusable_column() -> None:
    assert _get_inventory_tree(Row({"host_inventory": "not a tree"})) == ImmutableTree()


def test_get_delta_tree_without_the_column() -> None:
    assert _get_delta_tree(Row({})) == ImmutableDeltaTree()


def test_get_delta_tree_of_an_unusable_column() -> None:
    assert _get_delta_tree(Row({"invhist_delta": "not a tree"})) == ImmutableDeltaTree()
