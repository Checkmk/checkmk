#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.delta import compare_trees, ImmutableDeltaTree
from cmk.inventory.filtering import filter_tree, SDFilterChoice
from cmk.inventory.serialization import (
    deserialize_delta_tree,
    deserialize_tree,
    SDRawDeltaTree,
    serialize_delta_tree,
    serialize_tree,
)
from cmk.inventory.store import InventoryStore, make_meta
from cmk.inventory.structured_data import (
    ImmutableAttributes,
    ImmutableTree,
    make_retention_filter_choices,
    MutableTree,
    parse_visible_raw_path,
    RawIntervalFromConfig,
    RetentionInterval,
    SDKey,
    SDNodeName,
    SDPath,
    SDRetentionFilterChoices,
)

from .._fixtures import (
    empty_immutable_tree,
    empty_mutable_tree,
    filled_immutable_tree,
    filled_mutable_tree,
    immutable_tree,
    inventory_store,
)

_RETENTION_PATH = (SDNodeName("path"), SDNodeName("to"), SDNodeName("node"))


def _retention_config() -> Sequence[RawIntervalFromConfig]:
    return [
        RawIntervalFromConfig(
            interval=7,
            visible_raw_path="path.to.node",
            attributes=("choices", ["a1"]),
        ),
        RawIntervalFromConfig(
            interval=7,
            visible_raw_path="path.to.node",
            columns="all",
        ),
    ]


def _updated_tree(
    *, now: int, pairs_cache_info: Mapping[SDPath, tuple[int, int] | None]
) -> MutableTree:
    tree = MutableTree()
    tree.add(
        path=_RETENTION_PATH,
        pairs=[{SDKey("a1"): "value 1", SDKey("a2"): "value 2"}],
        key_columns=[SDKey("c0")],
        rows=[{SDKey("c0"): "row 0", SDKey("c1"): "value 1"}],
    )
    for choices in make_retention_filter_choices(
        now=now,
        raw_intervals_from_config=_retention_config(),
        pairs_cache_info=pairs_cache_info,
        columns_cache_info={},
    ):
        tree.update(now=now, previous_tree=ImmutableTree(), choices=choices)
    return tree


def _retained_pairs(
    *, now: int, pairs_cache_info: Mapping[SDPath, tuple[int, int] | None]
) -> Mapping[SDKey, RetentionInterval]:
    return (
        _updated_tree(now=now, pairs_cache_info=pairs_cache_info)
        .get_tree(_RETENTION_PATH)
        .attributes.retentions
    )


def test_retention_filter_keeps_the_columns_of_the_same_path() -> None:
    assert _updated_tree(now=10, pairs_cache_info={}).get_tree(
        _RETENTION_PATH
    ).table.retentions == {
        ("row 0",): {
            SDKey("c0"): RetentionInterval(10, 0, 7, "current"),
            SDKey("c1"): RetentionInterval(10, 0, 7, "current"),
        }
    }


def test_retention_filter_keeps_only_the_configured_pairs() -> None:
    assert set(_retained_pairs(now=10, pairs_cache_info={})) == {SDKey("a1")}


def test_retention_filter_defaults_the_cache_info() -> None:
    assert _retained_pairs(now=10, pairs_cache_info={}) == {
        SDKey("a1"): RetentionInterval(10, 0, 7, "current")
    }


def test_retention_filter_uses_the_cache_info() -> None:
    assert _retained_pairs(now=10, pairs_cache_info={_RETENTION_PATH: (2, 3)}) == {
        SDKey("a1"): RetentionInterval(2, 3, 7, "current")
    }


def test_retention_filter_defaults_an_unset_cache_info() -> None:
    assert _retained_pairs(now=10, pairs_cache_info={_RETENTION_PATH: None}) == {
        SDKey("a1"): RetentionInterval(10, 0, 7, "current")
    }


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


def test_serialize_empty_mut_tree() -> None:
    assert serialize_tree(empty_mutable_tree()) == {"Attributes": {}, "Table": {}, "Nodes": {}}


def test_serialize_filled_mut_tree() -> None:
    raw_tree = serialize_tree(filled_mutable_tree())
    assert not raw_tree["Attributes"]
    assert not raw_tree["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Attributes"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Table"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Attributes"][
        "Pairs"
    ] == {
        "na0": "NA 0",
        "na1": "NA 1",
    }
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Nodes"]

    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Attributes"]
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "KeyColumns"
    ] == ["nt0"]
    nt_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "Rows"
    ]
    assert len(nt_rows) == 2
    for row in [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]:
        assert row in nt_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Nodes"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Attributes"][
        "Pairs"
    ] == {
        "ta0": "TA 0",
        "ta1": "TA 1",
    }
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "KeyColumns"
    ] == ["ta0"]
    ta_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "Rows"
    ]
    assert len(ta_rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in ta_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Nodes"]


def test_deserialize_empty_imm_tree() -> None:
    assert deserialize_tree({}) == MutableTree()
    assert deserialize_tree({}) == ImmutableTree()


def test_deserialize_filled_imm_tree() -> None:
    tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "path-to-nta": {
                    "Attributes": {},
                    "Nodes": {
                        "na": {
                            "Attributes": {"Pairs": {"na0": "NA 0", "na1": "NA 1"}},
                            "Nodes": {},
                            "Table": {},
                        },
                        "nt": {
                            "Attributes": {},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["nt0"],
                                "Rows": [
                                    {"nt0": "NT 00", "nt1": "NT 01"},
                                    {"nt0": "NT 10", "nt1": "NT 11"},
                                ],
                            },
                        },
                        "ta": {
                            "Attributes": {"Pairs": {"ta0": "TA 0", "ta1": "TA 1"}},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["ta0"],
                                "Rows": [
                                    {"ta0": "TA 00", "ta1": "TA 01"},
                                    {"ta0": "TA 10", "ta1": "TA 11"},
                                ],
                            },
                        },
                    },
                    "Table": {},
                }
            },
        }
    )
    assert tree == filled_mutable_tree()
    assert tree == filled_immutable_tree()


def test_serialize_empty_delta_tree() -> None:
    assert serialize_delta_tree(compare_trees(empty_immutable_tree(), empty_immutable_tree())) == {
        "Attributes": {},
        "Table": {},
        "Nodes": {},
    }


def test_serialize_filled_delta_tree() -> None:
    raw_tree = serialize_delta_tree(compare_trees(empty_immutable_tree(), filled_immutable_tree()))
    assert not raw_tree["Attributes"]
    assert not raw_tree["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Attributes"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Table"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Attributes"][
        "Pairs"
    ] == {
        "na0": ("NA 0", None),
        "na1": ("NA 1", None),
    }
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Table"]
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("na")]["Nodes"]

    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Attributes"]
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "KeyColumns"
    ] == ["nt0"]
    nt_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Table"][
        "Rows"
    ]
    assert len(nt_rows) == 2
    for row in [
        {"nt0": ("NT 00", None), "nt1": ("NT 01", None)},
        {"nt0": ("NT 10", None), "nt1": ("NT 11", None)},
    ]:
        assert row in nt_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("nt")]["Nodes"]

    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Attributes"][
        "Pairs"
    ] == {
        "ta0": ("TA 0", None),
        "ta1": ("TA 1", None),
    }
    assert raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "KeyColumns"
    ] == ["ta0"]
    ta_rows = raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Table"][
        "Rows"
    ]
    assert len(ta_rows) == 2
    for row in [
        {"ta0": ("TA 00", None), "ta1": ("TA 01", None)},
        {"ta0": ("TA 10", None), "ta1": ("TA 11", None)},
    ]:
        assert row in ta_rows
    assert not raw_tree["Nodes"][SDNodeName("path-to-nta")]["Nodes"][SDNodeName("ta")]["Nodes"]


def test_deserialize_empty_delta_tree() -> None:
    assert len(ImmutableDeltaTree()) == 0


def test_deserialize_filled_delta_tree() -> None:
    delta_tree = deserialize_delta_tree(
        SDRawDeltaTree(
            Attributes={},
            Nodes={
                SDNodeName("path-to-nta"): SDRawDeltaTree(
                    Attributes={},
                    Nodes={
                        SDNodeName("na"): SDRawDeltaTree(
                            Attributes={
                                "Pairs": {
                                    SDKey("na0"): ("NA 0", None),
                                    SDKey("na1"): ("NA 1", None),
                                }
                            },
                            Nodes={},
                            Table={},
                        ),
                        SDNodeName("nt"): SDRawDeltaTree(
                            Attributes={},
                            Nodes={},
                            Table={
                                "KeyColumns": [SDKey("nt0")],
                                "Rows": [
                                    {SDKey("nt0"): ("NT 00", None), SDKey("nt1"): ("NT 01", None)},
                                    {SDKey("nt0"): ("NT 10", None), SDKey("nt1"): ("NT 11", None)},
                                ],
                            },
                        ),
                        SDNodeName("ta"): SDRawDeltaTree(
                            Attributes={
                                "Pairs": {
                                    SDKey("ta0"): ("TA 0", None),
                                    SDKey("ta1"): ("TA 1", None),
                                }
                            },
                            Nodes={},
                            Table={
                                "KeyColumns": [SDKey("ta0")],
                                "Rows": [
                                    {SDKey("ta0"): ("TA 00", None), SDKey("ta1"): ("TA 01", None)},
                                    {SDKey("ta0"): ("TA 10", None), SDKey("ta1"): ("TA 11", None)},
                                ],
                            },
                        ),
                    },
                    Table={},
                )
            },
            Table={},
        )
    )
    assert len(delta_tree) == 12
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 12


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
        HostName("tree_addresses_ordered"),
        HostName("tree_addresses_unordered"),
        HostName("tree_inv"),
        HostName("tree_new_addresses"),
        HostName("tree_new_addresses_arrays_memory"),
        HostName("tree_new_arrays"),
        HostName("tree_new_heute"),
        HostName("tree_new_interfaces"),
        HostName("tree_new_large_ora_tablespaces_fixed_len"),
        HostName("tree_new_large_ora_tablespaces_variable_len"),
        HostName("tree_new_memory"),
        HostName("tree_old_addresses"),
        HostName("tree_old_addresses_arrays_memory"),
        HostName("tree_old_arrays"),
        HostName("tree_old_heute"),
        HostName("tree_old_interfaces"),
        HostName("tree_old_large_ora_tablespaces"),
        HostName("tree_old_memory"),
        HostName("tree_status"),
    ],
)
def test_load_from(tree_name: HostName) -> None:
    inventory_store().load_inventory_tree(host_name=tree_name)


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
def test_save_and_load_real_tree(tree_name: HostName, tmp_path: Path) -> None:
    orig_tree = inventory_store().load_inventory_tree(host_name=tree_name)
    inv_store = InventoryStore(tmp_path)
    try:
        inv_store.save_inventory_tree(
            host_name=HostName("foo"),
            tree=orig_tree,
            meta=make_meta(do_archive=False),
        )
        loaded_tree = inv_store.load_inventory_tree(host_name=HostName("foo"))
        assert orig_tree == loaded_tree
    finally:
        shutil.rmtree(str(tmp_path))


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
    "filters, unavail",
    [
        (
            # container                   table                    attributes
            [
                SDFilterChoice(
                    path=(SDNodeName("hardware"), SDNodeName("components")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
                SDFilterChoice(
                    path=(SDNodeName("software"), SDNodeName("os")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
            ],
            [("hardware", "system"), ("software", "applications")],
        ),
    ],
)
def test_filter_real_tree(
    filters: Sequence[SDFilterChoice],
    unavail: Sequence[tuple[str, str]],
) -> None:
    tree = inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces"))
    filtered = filter_tree(tree, filters)
    assert id(tree) != id(filtered)
    assert tree != filtered
    for path in unavail:
        assert len(filtered.get_tree(tuple(SDNodeName(p) for p in path))) == 0


@pytest.mark.parametrize(
    "filters, amount_if_entries",
    [
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"),),
                    pairs="all",
                    columns="all",
                    nodes="all",
                )
            ],
            3178,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"),),
                    pairs=(
                        [
                            SDKey("total_interfaces"),
                            SDKey("total_ethernet_ports"),
                            SDKey("available_ethernet_ports"),
                        ]
                    ),
                    columns=(
                        [
                            SDKey("total_interfaces"),
                            SDKey("total_ethernet_ports"),
                            SDKey("available_ethernet_ports"),
                        ]
                    ),
                    nodes="nothing",
                ),
            ],
            None,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
            ],
            3178,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status")],
                    columns=[SDKey("admin_status")],
                    nodes="nothing",
                ),
            ],
            326,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("FOOBAR")],
                    columns=[SDKey("admin_status"), SDKey("FOOBAR")],
                    nodes="nothing",
                ),
            ],
            326,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("oper_status")],
                    columns=[SDKey("admin_status"), SDKey("oper_status")],
                    nodes="nothing",
                ),
            ],
            652,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("oper_status"), SDKey("FOOBAR")],
                    columns=[SDKey("admin_status"), SDKey("oper_status"), SDKey("FOOBAR")],
                    nodes="nothing",
                ),
            ],
            652,
        ),
    ],
)
def test_filter_networking_tree(
    filters: Sequence[SDFilterChoice],
    amount_if_entries: int | None,
) -> None:
    filtered = filter_tree(
        inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
        filters,
    )
    assert len(filtered.get_tree((SDNodeName("networking"),))) > 0
    assert len(filtered.get_tree((SDNodeName("hardware"),))) == 0
    assert len(filtered.get_tree((SDNodeName("software"),))) == 0

    if amount_if_entries is not None:
        interfaces = filtered.get_tree((SDNodeName("networking"), SDNodeName("interfaces")))
        assert len(interfaces) == amount_if_entries


def test_filter_networking_tree_empty() -> None:
    filtered = filter_tree(
        inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
        [
            SDFilterChoice(
                path=(SDNodeName("networking"),),
                pairs="nothing",
                columns="nothing",
                nodes="nothing",
            ),
        ],
    )
    assert len(filtered.get_tree((SDNodeName("networking"),))) == 0
    assert len(filtered.get_tree((SDNodeName("hardware"),))) == 0
    assert len(filtered.get_tree((SDNodeName("software"),))) == 0


@pytest.mark.parametrize(
    "raw_path, expected_path",
    [
        ("", ()),
        ("path-to.node_1", ("path-to", "node_1")),
    ],
)
def test_parse_visible_tree_path(raw_path: str, expected_path: SDPath) -> None:
    assert parse_visible_raw_path(raw_path) == expected_path


def test_legacy_tree() -> None:
    raw_tree = {
        "path-to": {
            "idx-node": [
                {
                    "idx-attr": "value",
                    "idx-enum": ["v1", 1.0, 2, None],
                    "idx-table": [{"idx-col": "value"}],
                    "idx-sub-node": {
                        "foo-node": {
                            "foo-attr": "value",
                        },
                    },
                    "idx-sub-idx-node": [
                        {
                            "bar-node": {
                                "bar-attr": "value",
                            },
                        },
                    ],
                },
            ],
            "node": {"attr": "value"},
            "table": [{"col": "value"}],
        },
    }
    # Object structure:
    # {
    #     'path-to': {
    #         'idx-node': {
    #             '0': {
    #                 'idx-attr': 'value',
    #                 'idx-sub-idx-node': {
    #                     '0': {
    #                         'bar-node': {
    #                             'bar-attr': 'value'
    #                         }
    #                     }
    #                 },
    #                 'idx-sub-node': {
    #                     'foo-node': {
    #                         'foo-attr': 'value'
    #                     }
    #                 },
    #                 'idx-table': [{
    #                     'idx-col': 'value'
    #                 }]
    #             }
    #         },
    #         'node': {
    #             'attr': 'value'
    #         },
    #         'table': [{
    #             'col': 'value'
    #         }]
    #     }
    # }

    tree = deserialize_tree(raw_tree)

    idx_node_attr = tree.get_tree((SDNodeName("path-to"), SDNodeName("idx-node"), SDNodeName("0")))
    assert len(idx_node_attr) > 0
    assert idx_node_attr.attributes.pairs == {"idx-attr": "value", "idx-enum": "v1, 1.0, 2"}
    assert not idx_node_attr.table.rows_by_ident
    assert not idx_node_attr.table.rows

    idx_sub_idx_node_attr = tree.get_tree(
        (
            SDNodeName("path-to"),
            SDNodeName("idx-node"),
            SDNodeName("0"),
            SDNodeName("idx-sub-idx-node"),
            SDNodeName("0"),
            SDNodeName("bar-node"),
        )
    )
    assert len(idx_sub_idx_node_attr) > 0
    assert idx_sub_idx_node_attr.attributes.pairs == {"bar-attr": "value"}
    assert not idx_sub_idx_node_attr.table.rows_by_ident
    assert not idx_sub_idx_node_attr.table.rows

    idx_sub_node_attr = tree.get_tree(
        (
            SDNodeName("path-to"),
            SDNodeName("idx-node"),
            SDNodeName("0"),
            SDNodeName("idx-sub-node"),
            SDNodeName("foo-node"),
        )
    )
    assert len(idx_sub_node_attr) > 0
    assert idx_sub_node_attr.attributes.pairs == {"foo-attr": "value"}
    assert not idx_sub_node_attr.table.rows_by_ident
    assert not idx_sub_node_attr.table.rows

    idx_table = tree.get_tree(
        (SDNodeName("path-to"), SDNodeName("idx-node"), SDNodeName("0"), SDNodeName("idx-table"))
    )
    assert len(idx_table) > 0
    assert not idx_table.attributes.pairs
    assert idx_table.table.rows_by_ident == {("value",): {"idx-col": "value"}}
    assert idx_table.table.rows == [{"idx-col": "value"}]

    attr_node = tree.get_tree((SDNodeName("path-to"), SDNodeName("node")))
    assert len(attr_node) > 0
    assert attr_node.attributes.pairs == {"attr": "value"}
    assert not attr_node.table.rows_by_ident
    assert not attr_node.table.rows

    table_node = tree.get_tree((SDNodeName("path-to"), SDNodeName("table")))
    assert len(table_node) > 0
    assert not table_node.attributes.pairs
    assert table_node.table.rows_by_ident == {("value",): {"col": "value"}}
    assert table_node.table.rows == [{"col": "value"}]


def test_update_attributes_from_previous() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {
                "Pairs": {"a1": "A1: prev", "a2": "A2: only prev"},
                "Retentions": {"a1": (1, 2, 3), "a2": (1, 2, 3)},
            },
            "Table": {},
            "Nodes": {},
        }
    )
    current_tree_ = MutableTree()
    current_tree_.add(
        path=(),
        pairs=[{SDKey("a1"): "A1: cur", SDKey("a3"): "A3: only cur"}],
    )
    choices = SDRetentionFilterChoices(path=(), interval=6)
    choices.add_pairs_choice(choice="all", cache_info=(4, 5))

    current_tree_.update(now=0, previous_tree=previous_tree, choices=choices)
    assert current_tree_.get_update_results() == {
        (): [
            "[Attributes] Added pairs: a2",
            "[Attributes] Keep until: a1 (15), a2 (6), a3 (15)",
        ]
    }

    current_tree = immutable_tree(current_tree_)
    assert current_tree.attributes.pairs == {
        "a1": "A1: cur",
        "a2": "A2: only prev",
        "a3": "A3: only cur",
    }
    assert current_tree.attributes.retentions == {
        "a1": RetentionInterval(4, 5, 6, "current"),
        "a2": RetentionInterval(1, 2, 3, "previous"),
        "a3": RetentionInterval(4, 5, 6, "current"),
    }


def test_update_from_previous_1() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}],
                "Retentions": {("KC",): {"c1": (1, 2, 3), "c2": (1, 2, 3)}},
            },
            "Nodes": {},
        }
    )
    current_tree_ = MutableTree()
    current_tree_.add(
        path=(),
        key_columns=[SDKey("kc")],
        rows=[
            {SDKey("kc"): "KC", SDKey("c1"): "C1: cur", SDKey("c3"): "C3: only cur"},
        ],
    )
    choices = SDRetentionFilterChoices(path=(), interval=6)
    choices.add_columns_choice(choice="all", cache_info=(4, 5))

    current_tree_.update(now=0, previous_tree=previous_tree, choices=choices)
    assert current_tree_.get_update_results() == {
        (): [
            "[Table] 'KC': Added row: c2, kc",
            "[Table] 'KC': Keep until: c1 (15), c2 (6), c3 (15), kc (15)",
        ]
    }

    current_tree = immutable_tree(current_tree_)
    assert current_tree.table.key_columns == ["kc"]
    assert current_tree.table.retentions == {
        ("KC",): {
            "c1": RetentionInterval(4, 5, 6, "current"),
            "c2": RetentionInterval(1, 2, 3, "previous"),
            "c3": RetentionInterval(4, 5, 6, "current"),
            "kc": RetentionInterval(4, 5, 6, "current"),
        }
    }
    assert current_tree.get_rows(()) == [
        {"c1": "C1: cur", "c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}
    ]


def test_update_from_previous_2() -> None:
    previous_tree = deserialize_tree(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}],
                "Retentions": {("KC",): {"c1": (1, 2, 3), "c2": (1, 2, 3)}},
            },
            "Nodes": {},
        }
    )
    current_tree_ = MutableTree()
    current_tree_.add(
        path=(),
        key_columns=[SDKey("kc")],
        rows=[
            {SDKey("kc"): "KC", SDKey("c3"): "C3: only cur"},
        ],
    )
    choices = SDRetentionFilterChoices(path=(), interval=6)
    choices.add_columns_choice(choice=[SDKey("c2"), SDKey("c3")], cache_info=(4, 5))
    current_tree_.update(now=0, previous_tree=previous_tree, choices=choices)
    assert current_tree_.get_update_results() == {
        (): [
            "[Table] 'KC': Added row: c2, kc",
            "[Table] 'KC': Keep until: c2 (6), c3 (15)",
        ],
    }

    current_tree = immutable_tree(current_tree_)
    assert current_tree.table.key_columns == ["kc"]
    assert current_tree.table.retentions == {
        ("KC",): {
            "c2": RetentionInterval(1, 2, 3, "previous"),
            "c3": RetentionInterval(4, 5, 6, "current"),
        }
    }
    assert current_tree.get_rows(()) == [{"c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}]


@pytest.mark.parametrize(
    "raw_retention_interval, expected_retention_interval",
    [
        ((1, 2, 3), RetentionInterval(1, 2, 3, "current")),
        ((4, 5, 6, "previous"), RetentionInterval(4, 5, 6, "previous")),
        ((7, 8, 9, "current"), RetentionInterval(7, 8, 9, "current")),
    ],
)
def test_deserialize_retention_interval(
    raw_retention_interval: (
        tuple[int, int, int] | tuple[int, int, int, Literal["previous", "current"]]
    ),
    expected_retention_interval: RetentionInterval,
) -> None:
    assert deserialize_tree(
        {
            "Attributes": {"Retentions": {SDKey("key"): raw_retention_interval}},
            "Table": {},
            "Nodes": {},
        }
    ).attributes.retentions == {SDKey("key"): expected_retention_interval}


@pytest.mark.parametrize(
    "retention_interval, expected_raw_retention_interval",
    [
        (RetentionInterval(1, 2, 3, "previous"), (1, 2, 3, "previous")),
        (RetentionInterval(4, 5, 6, "current"), (4, 5, 6, "current")),
    ],
)
def test_serialize_retention_interval(
    retention_interval: RetentionInterval,
    expected_raw_retention_interval: tuple[int, int, int, Literal["previous", "current"]],
) -> None:
    assert serialize_tree(
        ImmutableTree(attributes=ImmutableAttributes(retentions={SDKey("key"): retention_interval}))
    )["Attributes"]["Retentions"] == {SDKey("key"): expected_raw_retention_interval}
