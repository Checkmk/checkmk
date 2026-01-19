#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.structured_data import (
    _compare_trees,
    _DeltaDict,
    _deserialize_retention_interval,
    _parse_from_unzipped,
    _serialize_retention_interval,
    deserialize_delta_tree,
    deserialize_tree,
    filter_delta_tree,
    filter_tree,
    ImmutableAttributes,
    ImmutableDeltaTree,
    ImmutableTable,
    ImmutableTree,
    InventoryStore,
    make_meta,
    merge_trees,
    MutableTree,
    parse_from_gzipped,
    parse_visible_raw_path,
    RetentionInterval,
    SDDeltaValue,
    SDFilterChoice,
    SDKey,
    SDMeta,
    SDMetaAndRawTree,
    SDNodeName,
    SDPath,
    SDRawDeltaTree,
    SDRawTree,
    SDRetentionFilterChoices,
    serialize_delta_tree,
    serialize_tree,
)


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


def _make_immutable_tree(tree: MutableTree) -> ImmutableTree:
    return ImmutableTree(
        path=tree.path,
        attributes=ImmutableAttributes(
            pairs=tree.attributes.pairs,
            retentions=tree.attributes.retentions,
        ),
        table=ImmutableTable(
            key_columns=tree.table.key_columns,
            rows_by_ident=tree.table.rows_by_ident,
            retentions=tree.table.retentions,
        ),
        nodes_by_name={
            name: _make_immutable_tree(node) for name, node in tree.nodes_by_name.items()
        },
    )


def _create_empty_mut_tree() -> MutableTree:
    root = MutableTree()
    root.add(path=(SDNodeName("path-to-nta"), SDNodeName("nt")))
    root.add(path=(SDNodeName("path-to-nta"), SDNodeName("na")))
    root.add(path=(SDNodeName("path-to-nta"), SDNodeName("ta")))
    return root


def _create_empty_imm_tree() -> ImmutableTree:
    return _make_immutable_tree(_create_empty_mut_tree())


def _create_filled_mut_tree() -> MutableTree:
    root = MutableTree()
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("nt")),
        key_columns=[SDKey("nt0")],
        rows=[
            {SDKey("nt0"): "NT 00", SDKey("nt1"): "NT 01"},
            {SDKey("nt0"): "NT 10", SDKey("nt1"): "NT 11"},
        ],
    )
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("na")),
        pairs=[{SDKey("na0"): "NA 0", SDKey("na1"): "NA 1"}],
    )
    root.add(
        path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
        pairs=[{SDKey("ta0"): "TA 0", SDKey("ta1"): "TA 1"}],
        key_columns=[SDKey("ta0")],
        rows=[
            {SDKey("ta0"): "TA 00", SDKey("ta1"): "TA 01"},
            {SDKey("ta0"): "TA 10", SDKey("ta1"): "TA 11"},
        ],
    )
    return root


def _create_filled_imm_tree() -> ImmutableTree:
    return _make_immutable_tree(_create_filled_mut_tree())


def test_serialize_empty_mut_tree() -> None:
    assert serialize_tree(_create_empty_mut_tree()) == {"Attributes": {}, "Table": {}, "Nodes": {}}


def test_serialize_filled_mut_tree() -> None:
    raw_tree = serialize_tree(_create_filled_mut_tree())
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
    assert tree == _create_filled_mut_tree()
    assert tree == _create_filled_imm_tree()


def test_serialize_empty_delta_tree() -> None:
    assert serialize_delta_tree(
        _compare_trees(_create_empty_imm_tree(), _create_empty_imm_tree())
    ) == {
        "Attributes": {},
        "Table": {},
        "Nodes": {},
    }


def test_serialize_filled_delta_tree() -> None:
    raw_tree = serialize_delta_tree(
        _compare_trees(_create_empty_imm_tree(), _create_filled_imm_tree())
    )
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
    root = _create_empty_imm_tree()
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
    root = _create_filled_imm_tree()
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
    root = _create_filled_mut_tree()
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


def test_compare_tree_with_itself_1() -> None:
    empty_root = _create_empty_imm_tree()
    delta_tree = _compare_trees(empty_root, empty_root)
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_compare_tree_with_itself_2() -> None:
    filled_root = _create_filled_imm_tree()
    delta_tree = _compare_trees(filled_root, filled_root)
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_compare_tree_1() -> None:
    delta_tree = _compare_trees(_create_empty_imm_tree(), _create_filled_imm_tree())
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 12


def test_compare_tree_2() -> None:
    delta_tree = _compare_trees(_create_filled_imm_tree(), _create_empty_imm_tree())
    stats = delta_tree.get_stats()
    assert stats["new"] == 12
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_filter_delta_tree_nt() -> None:
    filtered = filter_delta_tree(
        _compare_trees(_create_filled_imm_tree(), _create_empty_imm_tree()),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("nt")),
                pairs=[SDKey("nt1")],
                columns=[SDKey("nt1")],
                nodes="nothing",
            )
        ],
    )

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))) == 0

    filtered_child = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))
    assert len(filtered_child) == 2
    assert filtered_child.path == ("path-to-nta", "nt")
    assert not filtered_child.attributes.pairs
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"nt1": SDDeltaValue(old=None, new="NT 01")},
        {"nt1": SDDeltaValue(old=None, new="NT 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_na() -> None:
    filtered = filter_delta_tree(
        _compare_trees(_create_filled_imm_tree(), _create_empty_imm_tree()),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("na")),
                pairs=[SDKey("na1")],
                columns=[SDKey("na1")],
                nodes="nothing",
            )
        ],
    )

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))) == 0

    filtered_child = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))
    assert len(filtered_child) == 1
    assert filtered_child.path == ("path-to-nta", "na")
    assert filtered_child.attributes.pairs == {"na1": SDDeltaValue(old=None, new="NA 1")}
    assert filtered_child.table.rows == []


def test_filter_delta_tree_ta() -> None:
    filtered = filter_delta_tree(
        _compare_trees(_create_filled_imm_tree(), _create_empty_imm_tree()),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta1")],
                columns=[SDKey("ta1")],
                nodes="nothing",
            )
        ],
    )

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0

    filtered_child = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(filtered_child) == 3
    assert filtered_child.path == ("path-to-nta", "ta")
    assert filtered_child.attributes.pairs == {"ta1": SDDeltaValue(old=None, new="TA 1")}
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"ta1": SDDeltaValue(old=None, new="TA 01")},
        {"ta1": SDDeltaValue(old=None, new="TA 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_nta_ta() -> None:
    filtered = filter_delta_tree(
        _compare_trees(_create_filled_imm_tree(), _create_empty_imm_tree()),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta0")],
                columns=[SDKey("ta0")],
                nodes="nothing",
            ),
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="nothing",
                columns=[SDKey("ta1")],
                nodes="nothing",
            ),
        ],
    )

    nta = filtered.get_tree((SDNodeName("path-to-nta"),))
    assert len(nta) == 5
    assert not nta.attributes.pairs
    assert nta.table.rows == []

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0

    filtered_ta = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(filtered_ta) == 5
    assert filtered_ta.attributes.pairs == {"ta0": SDDeltaValue(old=None, new="TA 0")}
    assert len(filtered_ta.table.rows) == 2
    for row in (
        {"ta0": SDDeltaValue(old=None, new="TA 00"), "ta1": SDDeltaValue(old=None, new="TA 01")},
        {"ta0": SDDeltaValue(old=None, new="TA 10"), "ta1": SDDeltaValue(old=None, new="TA 11")},
    ):
        assert row in filtered_ta.table.rows


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

    stats = _compare_trees(
        _make_immutable_tree(current_tree), _make_immutable_tree(previous_tree)
    ).get_stats()
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

    delta_tree = _compare_trees(
        _make_immutable_tree(current_tree), _make_immutable_tree(previous_tree)
    )
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

    delta_tree = _compare_trees(
        _make_immutable_tree(current_tree), _make_immutable_tree(previous_tree)
    )
    assert {k for r in delta_tree.table.rows for k in r} == expected_keys


def test_filter_tree_no_paths() -> None:
    assert len(filter_tree(_create_filled_imm_tree(), [])) == 0


def test_filter_tree_wrong_node() -> None:
    filtered = filter_tree(
        _create_filled_imm_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ],
    )
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))) == 6


def test_filter_tree_paths_no_keys() -> None:
    filtered = filter_tree(
        _create_filled_imm_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ],
    )

    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta0"))
        == "TA 0"
    )
    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta1"))
        == "TA 1"
    )
    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("foo")) is None
    )

    rows = filtered.get_rows((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in rows


def test_filter_tree_paths_and_keys() -> None:
    filtered = filter_tree(
        _create_filled_imm_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta1")],
                columns=[SDKey("ta1")],
                nodes="all",
            ),
        ],
    )

    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta1"))
        == "TA 1"
    )
    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("foo")) is None
    )

    rows = filtered.get_rows((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(rows) == 2
    for row in [
        {"ta1": "TA 01"},
        {"ta1": "TA 11"},
    ]:
        assert row in rows


def test_filter_tree_mixed() -> None:
    filled_root_ = _create_filled_mut_tree()
    filled_root_.add(
        path=(SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node1")),
        pairs=[{SDKey("ak11"): "Another value 11", SDKey("ak12"): "Another value 12"}],
    )
    filled_root_.add(
        path=(SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node2")),
        key_columns=[SDKey("ak21")],
        rows=[
            {
                SDKey("ak21"): "Another value 211",
                SDKey("ak22"): "Another value 212",
            },
            {
                SDKey("ak21"): "Another value 221",
                SDKey("ak22"): "Another value 222",
            },
        ],
    )

    filtered = filter_tree(
        _make_immutable_tree(filled_root_),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to"), SDNodeName("another")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta0")],
                columns=[SDKey("ta1")],
                nodes="all",
            ),
        ],
    )

    assert len(filtered) == 9
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0
    assert (
        len(filtered.get_tree((SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node1"))))
        == 2
    )
    assert (
        len(filtered.get_tree((SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node2"))))
        == 4
    )


def _get_inventory_store() -> InventoryStore:
    return InventoryStore(Path(__file__).parent / "tree_test_data")


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
    _get_inventory_store().load_inventory_tree(host_name=tree_name)


@pytest.mark.parametrize(
    "do_archive",
    [
        pytest.param(True, id="do-archive"),
        pytest.param(False, id="do-not-archive"),
    ],
)
def test_save_inventory_tree(tmp_path: Path, do_archive: bool) -> None:
    host_name = HostName("heute")
    tree = MutableTree()
    tree.add(
        path=(SDNodeName("path-to"), SDNodeName("node")), pairs=[{SDKey("foo"): 1, SDKey("bär"): 2}]
    )
    inv_store = InventoryStore(tmp_path)
    inv_store.save_inventory_tree(
        host_name=host_name,
        tree=tree,
        meta=make_meta(do_archive=do_archive),
    )

    assert (tmp_path / "var/check_mk/inventory/heute.json").exists()
    assert not (tmp_path / "var/check_mk/inventory/heute").exists()
    assert (tmp_path / "var/check_mk/inventory/heute.json.gz").exists()
    assert not (tmp_path / "var/check_mk/inventory/heute.gz").exists()

    with (tmp_path / "var/check_mk/inventory/heute.json.gz").open("rb") as f:
        content = f.read()

    # Similiar to InventoryUpdater:
    meta_and_raw_tree = parse_from_gzipped(content)
    assert meta_and_raw_tree["meta"]["version"] == "1"
    assert meta_and_raw_tree["meta"]["do_archive"] is do_archive

    expected_raw_tree = serialize_tree(tree)
    assert meta_and_raw_tree["raw_tree"]["Attributes"] == expected_raw_tree["Attributes"]
    assert meta_and_raw_tree["raw_tree"]["Table"] == expected_raw_tree["Table"]
    assert meta_and_raw_tree["raw_tree"]["Nodes"] == expected_raw_tree["Nodes"]


def test_save_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("heute")
    tree = MutableTree()
    tree.add(
        path=(SDNodeName("path-to"), SDNodeName("node")), pairs=[{SDKey("foo"): 1, SDKey("bär"): 2}]
    )
    inv_store = InventoryStore(tmp_path)
    inv_store.save_status_data_tree(host_name=host_name, tree=tree)

    assert (tmp_path / "tmp/check_mk/status_data/heute.json").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/heute").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/heute.json.gz").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/heute.gz").exists()


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param(
            {"Attributes": {}, "Table": {}, "Nodes": {}},
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="missing-version:missing-meta",
        ),
        pytest.param(
            {
                "meta_version": "0",
                "meta_do_archive": True,
                "Attributes": {},
                "Table": {},
                "Nodes": {},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=0:do-archive",
        ),
        pytest.param(
            {
                "meta_version": "0",
                "meta_do_archive": False,
                "Attributes": {},
                "Table": {},
                "Nodes": {},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=False),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=0:do-not-archive",
        ),
        pytest.param(
            {
                "meta": {"version": "1", "do_archive": True},
                "raw_tree": {"Attributes": {}, "Table": {}, "Nodes": {}},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=1:do-archive",
        ),
        pytest.param(
            {
                "meta": {"version": "1", "do_archive": False},
                "raw_tree": {"Attributes": {}, "Table": {}, "Nodes": {}},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=False),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=1:do-archive",
        ),
    ],
)
def test_parse_from_unzipped(raw: Mapping[str, object], expected: SDMetaAndRawTree) -> None:
    assert _parse_from_unzipped(raw) == expected


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
    assert len(_get_inventory_store().load_inventory_tree(host_name=tree_name)) > 0


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
    inv_store = _get_inventory_store()
    tree_x = inv_store.load_inventory_tree(host_name=tree_name_x)
    tree_y = inv_store.load_inventory_tree(host_name=tree_name_y)

    if tree_name_x == tree_name_y:
        assert tree_x == tree_y
    else:
        assert tree_x != tree_y


def test_real_tree_order() -> None:
    inv_store = _get_inventory_store()
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
    orig_tree = _get_inventory_store().load_inventory_tree(host_name=tree_name)
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
    assert len(_get_inventory_store().load_inventory_tree(host_name=tree_name)) == result


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
    tree = _get_inventory_store().load_inventory_tree(host_name=tree_name)
    stats = _compare_trees(tree, tree).get_stats()
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
    inv_store = _get_inventory_store()
    old_tree = inv_store.load_inventory_tree(host_name=tree_name_old)
    new_tree = inv_store.load_inventory_tree(host_name=tree_name_new)
    stats = _compare_trees(new_tree, old_tree).get_stats()
    assert (stats["new"], stats["changed"], stats["removed"]) == result


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
    tree = _get_inventory_store().load_inventory_tree(host_name=tree_name)
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
    tree = _get_inventory_store().load_inventory_tree(host_name=tree_name)
    assert len(list(tree.nodes_by_name.values())) == amount_of_nodes


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
    inv_store = _get_inventory_store()
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
    inv_store = _get_inventory_store()
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
    tree = _get_inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces"))
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
    amount_if_entries: int,
) -> None:
    filtered = filter_tree(
        _get_inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
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
        _get_inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
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
        ("", tuple()),
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
            "[Table] 'KC': Added row: message",
            "[Table] 'KC': Keep until: message",
        ]
    }

    current_tree = _make_immutable_tree(current_tree_)
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
            "[Table] 'KC': Added row: message",
            "[Table] 'KC': Keep until: message",
        ],
    }

    current_tree = _make_immutable_tree(current_tree_)
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
    assert _deserialize_retention_interval(raw_retention_interval) == expected_retention_interval


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
    assert _serialize_retention_interval(retention_interval) == expected_raw_retention_interval


@pytest.mark.parametrize(
    "keep_identical, result",
    [
        pytest.param(
            False,
            _DeltaDict(
                result={
                    SDKey("key2"): SDDeltaValue(old=None, new="val2"),
                    SDKey("key3"): SDDeltaValue(old="val3", new=None),
                    SDKey("key4"): SDDeltaValue(old="val4-old", new="val4-new"),
                },
                has_changes=True,
            ),
            id="do-not-keep-identical",
        ),
        pytest.param(
            True,
            _DeltaDict(
                result={
                    SDKey("key1"): SDDeltaValue(old="val1", new="val1"),
                    SDKey("key2"): SDDeltaValue(old=None, new="val2"),
                    SDKey("key3"): SDDeltaValue(old="val3", new=None),
                    SDKey("key4"): SDDeltaValue(old="val4-old", new="val4-new"),
                },
                has_changes=True,
            ),
            id="keep-identical",
        ),
    ],
)
def test__delta_dict(keep_identical: bool, result: _DeltaDict) -> None:
    assert (
        _DeltaDict.compare(
            left={
                SDKey("key1"): "val1",
                SDKey("key2"): "val2",
                SDKey("key4"): "val4-new",
            },
            right={
                SDKey("key1"): "val1",
                SDKey("key3"): "val3",
                SDKey("key4"): "val4-old",
            },
            keep_identical=keep_identical,
        )
        == result
    )
