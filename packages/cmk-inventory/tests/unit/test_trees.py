#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.trees import (
    compare_sd_values,
    ImmutableTree,
    MutableTree,
    parse_visible_raw_path,
    RetentionInterval,
    SDKey,
    SDNodeName,
    SDPath,
    SDValue,
    sort_missing_values_first,
)

from ._fixtures import (
    empty_immutable_tree,
    filled_immutable_tree,
    filled_mutable_tree,
    immutable_tree,
    inventory_store,
)


def test_retention_interval_valid_until() -> None:
    assert RetentionInterval(100, 20, 3, "current").valid_until == 120


def test_retention_interval_keep_until() -> None:
    assert RetentionInterval(100, 20, 3, "current").keep_until == 123


@pytest.mark.parametrize(
    "left, right",
    [
        pytest.param(
            MutableTree(nodes_by_name={SDNodeName("lnode"): MutableTree()}),
            MutableTree(nodes_by_name={SDNodeName("rnode"): MutableTree()}),
            id="m-m",
        ),
        pytest.param(
            MutableTree(nodes_by_name={SDNodeName("lnode"): MutableTree()}),
            ImmutableTree(nodes_by_name={SDNodeName("rnode"): ImmutableTree()}),
            id="m-i",
        ),
        pytest.param(
            ImmutableTree(nodes_by_name={SDNodeName("lnode"): ImmutableTree()}),
            MutableTree(nodes_by_name={SDNodeName("rnode"): MutableTree()}),
            id="i-m",
        ),
        pytest.param(
            ImmutableTree(nodes_by_name={SDNodeName("lnode"): ImmutableTree()}),
            ImmutableTree(nodes_by_name={SDNodeName("rnode"): ImmutableTree()}),
            id="i-i",
        ),
    ],
)
def test_equality_with_non_empty_nodes(
    left: MutableTree | ImmutableTree, right: MutableTree | ImmutableTree
) -> None:
    assert left == right


def test_get_tree_empty() -> None:
    root = empty_immutable_tree()
    assert len(root) == 0
    assert root.get_tree((SDNodeName("path-to-nta"),)).path == ("path-to-nta",)
    assert root.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt"))).path == (
        "path-to-nta",
        "nt",
    )
    assert root.get_tree((SDNodeName("path-to-nta"), SDNodeName("na"))).path == (
        "path-to-nta",
        "na",
    )
    assert root.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta"))).path == (
        "path-to-nta",
        "ta",
    )


def test_get_tree_not_empty() -> None:
    root = filled_immutable_tree()
    nta = root.get_tree((SDNodeName("path-to-nta"),))
    nt = root.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))
    na = root.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))
    ta = root.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(root) == 12
    assert len(nta) == 12
    assert len(nt) == 4
    assert len(na) == 2
    assert len(ta) == 6

    assert nta.path == ("path-to-nta",)
    assert nt.path == ("path-to-nta", "nt")
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("nt")), SDKey("foo")) is None
    nt_rows = root.get_rows((SDNodeName("path-to-nta"), SDNodeName("nt")))
    for row in [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]:
        assert row in nt_rows

    assert na.path == ("path-to-nta", "na")
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("na")), SDKey("na0")) == "NA 0"
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("na")), SDKey("na1")) == "NA 1"
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("na")), SDKey("foo")) is None
    assert not root.get_rows((SDNodeName("path-to-nta"), SDNodeName("na")))

    assert ta.path == ("path-to-nta", "ta")
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta0")) == "TA 0"
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta1")) == "TA 1"
    assert root.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("foo")) is None
    ta_rows = root.get_rows((SDNodeName("path-to-nta"), SDNodeName("ta")))
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in ta_rows


def test_add_or_rows() -> None:
    root = filled_mutable_tree()
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("node")),
        pairs=[{SDKey("sn0"): "SN 0", SDKey("sn1"): "SN 1"}],
        key_columns=[SDKey("sn0")],
        rows=[
            {SDKey("sn0"): "SN 00", SDKey("sn1"): "SN 01"},
            {SDKey("sn0"): "SN 10", SDKey("sn1"): "SN 11"},
        ],
    )
    assert len(root) == 18


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
def test_load_real_tree(tree_name: HostName) -> None:
    assert len(inventory_store().load_inventory_tree(host_name=tree_name)) > 0


@pytest.mark.parametrize(
    "tree_name_x",
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
@pytest.mark.parametrize(
    "tree_name_y",
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
def test_real_tree_is_equal(tree_name_x: HostName, tree_name_y: HostName) -> None:
    inv_store = inventory_store()
    tree_x = inv_store.load_inventory_tree(host_name=tree_name_x)
    tree_y = inv_store.load_inventory_tree(host_name=tree_name_y)

    if tree_name_x == tree_name_y:
        assert tree_x == tree_y
    else:
        assert tree_x != tree_y


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
def test_count_entries(tree_name: HostName, result: int) -> None:
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
def test_get_node(
    tree_name: HostName, edges_t: Iterable[SDNodeName], edges_f: Iterable[SDNodeName]
) -> None:
    tree = inventory_store().load_inventory_tree(host_name=tree_name)
    for edge_t in edges_t:
        assert len(tree.get_tree((edge_t,))) > 0
    for edge_f in edges_f:
        assert len(tree.get_tree((edge_f,))) == 0


@pytest.mark.parametrize(
    "tree_name, amount_of_nodes",
    [
        (HostName("tree_old_addresses_arrays_memory"), 2),
        (HostName("tree_old_addresses"), 1),
        (HostName("tree_old_arrays"), 1),
        (HostName("tree_old_interfaces"), 3),
        (HostName("tree_old_memory"), 1),
        (HostName("tree_old_heute"), 3),
    ],
)
def test_amount_of_nodes(tree_name: HostName, amount_of_nodes: int) -> None:
    tree = inventory_store().load_inventory_tree(host_name=tree_name)
    assert len(list(tree.nodes_by_name.values())) == amount_of_nodes


@pytest.mark.parametrize(
    "raw_path, expected_path",
    [
        ("", ()),
        ("path-to.node_1", ("path-to", "node_1")),
    ],
)
def test_parse_visible_tree_path(raw_path: str, expected_path: SDPath) -> None:
    assert parse_visible_raw_path(raw_path) == expected_path


def _tree_with(
    *,
    path: SDPath = (),
    pairs: Sequence[Mapping[SDKey, str]] = (),
    rows: Sequence[Mapping[SDKey, str]] = (),
) -> MutableTree:
    tree = MutableTree()
    tree.add(path=path, pairs=pairs, key_columns=[SDKey("key")], rows=rows)
    return tree


_UNEQUAL_TREES = [
    pytest.param(
        _tree_with(pairs=[{SDKey("key"): "left"}]),
        _tree_with(pairs=[{SDKey("key"): "right"}]),
        id="different-attributes",
    ),
    pytest.param(
        _tree_with(rows=[{SDKey("key"): "left"}]),
        _tree_with(),
        id="row-only-left",
    ),
    pytest.param(
        _tree_with(),
        _tree_with(rows=[{SDKey("key"): "right"}]),
        id="row-only-right",
    ),
    pytest.param(
        _tree_with(path=(SDNodeName("node"),), pairs=[{SDKey("key"): "value"}]),
        _tree_with(),
        id="node-only-left",
    ),
    pytest.param(
        _tree_with(),
        _tree_with(path=(SDNodeName("node"),), pairs=[{SDKey("key"): "value"}]),
        id="node-only-right",
    ),
]


@pytest.mark.parametrize("left, right", _UNEQUAL_TREES)
def test_mutable_trees_with_different_content_are_unequal(
    left: MutableTree, right: MutableTree
) -> None:
    assert left != right


@pytest.mark.parametrize("left, right", _UNEQUAL_TREES)
def test_immutable_trees_with_different_content_are_unequal(
    left: MutableTree, right: MutableTree
) -> None:
    assert immutable_tree(left) != immutable_tree(right)


@pytest.mark.parametrize(
    "tree",
    [
        pytest.param(MutableTree(), id="mutable"),
        pytest.param(ImmutableTree(), id="immutable"),
    ],
)
def test_a_tree_is_unequal_to_a_non_tree(tree: MutableTree | ImmutableTree) -> None:
    assert tree != "tree"


def _always_two(_val_a: SDValue, _val_b: SDValue) -> int:
    return 2


@pytest.mark.parametrize(
    "val_a, val_b, result",
    [
        pytest.param(None, None, 0, id="both-missing"),
        pytest.param(None, 0, -1, id="first-missing"),
        pytest.param(0, None, 1, id="second-missing"),
        pytest.param(0, 0, 2, id="none-missing"),
    ],
)
def test_sort_missing_values_first(val_a: SDValue, val_b: SDValue, result: int) -> None:
    assert sort_missing_values_first(_always_two)(val_a, val_b) == result


@pytest.mark.parametrize(
    "val_a, val_b, result",
    [
        pytest.param(0, 0, 0, id="equal-numbers"),
        pytest.param(1, 0, 1, id="greater-number"),
        pytest.param(0, 1, -1, id="smaller-number"),
        pytest.param("a", "b", -1, id="smaller-text"),
        pytest.param("b", "a", 1, id="greater-text"),
    ],
)
def test_compare_sd_values(val_a: SDValue, val_b: SDValue, result: int) -> None:
    assert compare_sd_values(val_a, val_b) == result


def test_compare_sd_values_rejects_mixed_types() -> None:
    with pytest.raises(TypeError):
        compare_sd_values("a", 1)
