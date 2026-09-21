#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.delta import compare_trees, SDDeltaValue
from cmk.inventory.serialization import deserialize_tree
from cmk.inventory.structured_data import (
    MutableTree,
    SDKey,
)

from ._fixtures import (
    empty_immutable_tree,
    filled_immutable_tree,
    immutable_tree,
    inventory_store,
)


def test_compare_tree_with_itself_1() -> None:
    empty_root = empty_immutable_tree()
    delta_tree = compare_trees(empty_root, empty_root)
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_compare_tree_with_itself_2() -> None:
    filled_root = filled_immutable_tree()
    delta_tree = compare_trees(filled_root, filled_root)
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_compare_tree_1() -> None:
    delta_tree = compare_trees(empty_immutable_tree(), filled_immutable_tree())
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 12


def test_compare_tree_2() -> None:
    delta_tree = compare_trees(filled_immutable_tree(), empty_immutable_tree())
    stats = delta_tree.get_stats()
    assert stats["new"] == 12
    assert stats["changed"] == 0
    assert stats["removed"] == 0


@pytest.mark.parametrize(
    "previous_pairs, current_pairs, result",
    [
        ({}, {}, (0, 0, 0)),
        ({"k0": "v0"}, {"k0": "v0"}, (0, 0, 0)),
        ({"k0": "v0"}, {}, (0, 0, 1)),
        ({}, {"k0": "v0"}, (1, 0, 0)),
        ({"k0": "v00"}, {"k0": "v01"}, (0, 1, 0)),
        (
            {
                "k0": "v0",
                "k1": "v1",
            },
            {"k1": "v1"},
            (0, 0, 1),
        ),
        (
            {"k1": "v1"},
            {
                "k0": "v0",
                "k1": "v1",
            },
            (1, 0, 0),
        ),
        (
            {
                "k0": "v00",
                "k1": "v1",
            },
            {
                "k0": "v01",
                "k1": "v1",
            },
            (0, 1, 0),
        ),
    ],
)
def test_difference_pairs(
    previous_pairs: Mapping[SDKey, str],
    current_pairs: Mapping[SDKey, str],
    result: tuple[int, int, int],
) -> None:
    previous_tree = MutableTree()
    previous_tree.add(path=(), pairs=[previous_pairs])

    current_tree = MutableTree()
    current_tree.add(path=(), pairs=[current_pairs])

    stats = compare_trees(immutable_tree(current_tree), immutable_tree(previous_tree)).get_stats()
    assert (stats["new"], stats["changed"], stats["removed"]) == result


@pytest.mark.parametrize(
    "previous_rows, current_rows, result",
    [
        ([], [], (0, 0, 0)),
        ([{"id": "1", "val": 0}], [], (0, 0, 2)),
        ([], [{"id": "1", "val": 0}], (2, 0, 0)),
        ([{"id": "1", "val": 0}], [{"id": "1", "val": 0}], (0, 0, 0)),
        ([{"id": "1", "val": 0}, {"id": "2", "val": 1}], [{"id": "1", "val": 0}], (0, 0, 2)),
        ([{"id": "1", "val": 0}], [{"id": "1", "val": 0}, {"id": "2", "val": 1}], (2, 0, 0)),
        ([{"id": "1", "val1": 1}], [{"id": "1", "val1": 1, "val2": 1}], (1, 0, 0)),
        ([{"id": "1", "val": 0}], [{"id": "1", "val": 1}], (0, 1, 0)),
        ([{"id": "1", "val1": 1, "val2": -1}], [{"id": "1", "val1": 1}], (0, 0, 1)),
        (
            [{"id": "1", "val1": 0}, {"id": "2", "val1": 0, "val2": 0}, {"id": "3", "val1": 0}],
            [{"id": "1", "val1": 1}, {"id": "2", "val1": 0}, {"id": "3", "val1": 0, "val2": 1}],
            (1, 1, 1),
        ),
        (
            [{"id": "1", "val1": 1}, {"id": "2", "val1": 1}],
            [{"id": "1", "val1": 1, "val2": -1}, {"id": "2", "val1": 1, "val2": -1}],
            (2, 0, 0),
        ),
        (
            [{"id": "1", "val": 1}, {"id": "2", "val": 3}],
            [{"id": "1", "val": 2}, {"id": "2", "val": 4}],
            (0, 2, 0),
        ),
        (
            [{"id": "1", "val1": 1, "val2": -1}, {"id": "2", "val1": 1, "val2": -1}],
            [{"id": "1", "val1": 1}, {"id": "2", "val1": 1}],
            (0, 0, 2),
        ),
        (
            [{"id": "2", "val": 1}, {"id": "3", "val": 3}, {"id": "1", "val": 0}],
            [{"id": "2", "val": 2}, {"id": "1", "val": 0}, {"id": "3", "val": 4}],
            (0, 2, 0),
        ),
        (
            [{"id": "1", "val": 1}, {"id": "2", "val": 3}, {"id": "3", "val": 0}],
            [
                {"id": "0", "val": 2},
                {"id": "1", "val": 0},
                {"id": "2", "val": 4},
                {"id": "3", "val": 1},
            ],
            (2, 3, 0),
        ),
    ],
)
def test_difference_rows(
    previous_rows: Sequence[Mapping[SDKey, str | int]],
    current_rows: Sequence[Mapping[SDKey, str | int]],
    result: tuple[int, int, int],
) -> None:
    previous_tree = MutableTree()
    previous_tree.add(path=(), key_columns=[SDKey("id")], rows=previous_rows)

    current_tree = MutableTree()
    current_tree.add(path=(), key_columns=[SDKey("id")], rows=current_rows)

    delta_tree = compare_trees(immutable_tree(current_tree), immutable_tree(previous_tree))
    if any(result):
        assert len(delta_tree) > 0
    else:
        assert len(delta_tree) == 0

    stats = delta_tree.get_stats()
    assert (stats["new"], stats["changed"], stats["removed"]) == result


@pytest.mark.parametrize(
    "previous_row, current_row, expected_keys",
    [
        ({}, {}, set()),
        ({"id": "id", "val": "val"}, {"id": "id", "val": "val"}, set()),
        ({"id": "id", "val": "val"}, {"id": "id"}, {"id", "val"}),
        ({"id": "id"}, {"id": "id", "val": "val"}, {"id", "val"}),
        ({"id": "id1", "val": "val"}, {"id": "id2", "val": "val"}, {"id", "val"}),
    ],
)
def test_difference_rows_keys(
    previous_row: Mapping[SDKey, str],
    current_row: Mapping[SDKey, str],
    expected_keys: set[str],
) -> None:
    previous_tree = MutableTree()
    previous_tree.add(path=(), key_columns=[SDKey("id")], rows=[previous_row])

    current_tree = MutableTree()
    current_tree.add(path=(), key_columns=[SDKey("id")], rows=[current_row])

    delta_tree = compare_trees(immutable_tree(current_tree), immutable_tree(previous_tree))
    assert {k for r in delta_tree.table.rows for k in r} == expected_keys


@pytest.mark.parametrize(
    "tree_name",
    [
        HostName("tree_old_addresses_arrays_memory"),
        HostName("tree_old_addresses"),
        HostName("tree_old_arrays"),
        HostName("tree_old_interfaces"),
        HostName("tree_old_memory"),
        HostName("tree_old_heute"),
        HostName("tree_new_addresses_arrays_memory"),
        HostName("tree_new_addresses"),
        HostName("tree_new_arrays"),
        HostName("tree_new_interfaces"),
        HostName("tree_new_memory"),
        HostName("tree_new_heute"),
    ],
)
def test_compare_real_tree_with_itself(tree_name: HostName) -> None:
    tree = inventory_store().load_inventory_tree(host_name=tree_name)
    stats = compare_trees(tree, tree).get_stats()
    assert (stats["new"], stats["changed"], stats["removed"]) == (0, 0, 0)


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


def test_compare_trees_pairs() -> None:
    assert compare_trees(
        deserialize_tree(
            {
                "Attributes": {"Pairs": {"key1": "val1", "key2": "val2", "key4": "val4-new"}},
                "Table": {},
                "Nodes": {},
            }
        ),
        deserialize_tree(
            {
                "Attributes": {"Pairs": {"key1": "val1", "key3": "val3", "key4": "val4-old"}},
                "Table": {},
                "Nodes": {},
            }
        ),
    ).attributes.pairs == {
        SDKey("key2"): SDDeltaValue(old=None, new="val2"),
        SDKey("key3"): SDDeltaValue(old="val3", new=None),
        SDKey("key4"): SDDeltaValue(old="val4-old", new="val4-new"),
    }


def test_compare_trees_rows() -> None:
    assert compare_trees(
        deserialize_tree(
            {
                "Attributes": {},
                "Table": {
                    "KeyColumns": ["key1"],
                    "Rows": [{"key1": "val1", "key2": "val2", "key4": "val4-new"}],
                },
                "Nodes": {},
            }
        ),
        deserialize_tree(
            {
                "Attributes": {},
                "Table": {
                    "KeyColumns": ["key1"],
                    "Rows": [{"key1": "val1", "key3": "val3", "key4": "val4-old"}],
                },
                "Nodes": {},
            }
        ),
    ).table.rows == [
        {
            SDKey("key1"): SDDeltaValue(old="val1", new="val1"),
            SDKey("key2"): SDDeltaValue(old=None, new="val2"),
            SDKey("key3"): SDDeltaValue(old="val3", new=None),
            SDKey("key4"): SDDeltaValue(old="val4-old", new="val4-new"),
        }
    ]
