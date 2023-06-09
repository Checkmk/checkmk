#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import pytest

from tests.testlib import cmk_path

from cmk.utils.structured_data import (
    _compare_attributes,
    _compare_tables,
    Attributes,
    ImmutableDeltaTree,
    ImmutableTree,
    MutableTree,
    parse_visible_raw_path,
    RetentionIntervals,
    SDFilter,
    SDNodeName,
    SDPath,
    StructuredDataNode,
    Table,
    TreeStore,
)
from cmk.utils.type_defs import HostName


def _create_empty_tree() -> ImmutableTree:
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes
    root = StructuredDataNode()
    root.setdefault_node(("path-to", "nta", "nt"))
    root.setdefault_node(("path-to", "nta", "na"))
    root.setdefault_node(("path-to", "nta", "ta"))
    return ImmutableTree(root)


def _create_filled_tree() -> ImmutableTree:
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes
    root = StructuredDataNode()
    nt = root.setdefault_node(("path-to", "nta", "nt"))
    na = root.setdefault_node(("path-to", "nta", "na"))
    ta = root.setdefault_node(("path-to", "nta", "ta"))

    nt.table.add_key_columns(["nt0"])
    nt.table.add_rows(
        [
            {"nt0": "NT 00", "nt1": "NT 01"},
            {"nt0": "NT 10", "nt1": "NT 11"},
        ]
    )

    na.attributes.add_pairs({"na0": "NA 0", "na1": "NA 1"})

    ta.table.add_key_columns(["ta0"])
    ta.table.add_rows(
        [
            {"ta0": "TA 00", "ta1": "TA 01"},
            {"ta0": "TA 10", "ta1": "TA 11"},
        ]
    )
    ta.attributes.add_pairs({"ta0": "TA 0", "ta1": "TA 1"})
    return ImmutableTree(root)


def test_get_node() -> None:
    root = _create_empty_tree().tree

    nta = root.get_node(("path-to", "nta"))
    nt = root.get_node(("path-to", "nta", "nt"))
    na = root.get_node(("path-to", "nta", "na"))
    ta = root.get_node(("path-to", "nta", "ta"))

    assert nta is not None
    assert nt is not None
    assert na is not None
    assert ta is not None

    assert root.get_node(("path-to", "unknown")) is None


def test_set_path() -> None:
    root = _create_empty_tree().tree

    nta = root.get_node(("path-to", "nta"))
    nt = root.get_node(("path-to", "nta", "nt"))
    na = root.get_node(("path-to", "nta", "na"))
    ta = root.get_node(("path-to", "nta", "ta"))

    assert nta is not None
    assert nta.path == ("path-to", "nta")

    assert nt is not None
    assert nt.path == ("path-to", "nta", "nt")

    assert na is not None
    assert na.path == ("path-to", "nta", "na")

    assert ta is not None
    assert ta.path == ("path-to", "nta", "ta")


def test_set_path_sub_nodes() -> None:
    root = _create_empty_tree().tree
    nta = root.get_node(("path-to", "nta"))

    sub_node = StructuredDataNode()
    sub_node.setdefault_node(("sub-path-to", "sub-node"))

    assert nta is not None
    nta.add_node(("node",), sub_node)

    path_to_node = root.get_node(("path-to", "nta", "node", "sub-path-to"))
    assert path_to_node is not None
    assert path_to_node.path == ("path-to", "nta", "node", "sub-path-to")

    path_to_sub_node = root.get_node(("path-to", "nta", "node", "sub-path-to", "sub-node"))
    assert path_to_sub_node is not None
    assert path_to_sub_node.path == ("path-to", "nta", "node", "sub-path-to", "sub-node")


def test_empty_but_different_structure() -> None:
    root = _create_empty_tree().tree

    nt = root.get_node(("path-to", "nta", "nt"))
    na = root.get_node(("path-to", "nta", "na"))
    ta = root.get_node(("path-to", "nta", "ta"))

    assert nt is not None
    assert not nt.attributes
    assert not nt.table

    assert na is not None
    assert not na.attributes
    assert not na.table

    assert ta is not None
    assert not ta.attributes
    assert not ta.table

    assert not root
    assert root.count_entries() == 0
    assert root != StructuredDataNode()


def test_not_empty() -> None:
    root = _create_filled_tree().tree

    nt = root.get_node(("path-to", "nta", "nt"))
    na = root.get_node(("path-to", "nta", "na"))
    ta = root.get_node(("path-to", "nta", "ta"))

    assert nt is not None
    assert not nt.attributes
    assert nt.table.rows_by_ident == {
        ("NT 00",): {"nt0": "NT 00", "nt1": "NT 01"},
        ("NT 10",): {"nt0": "NT 10", "nt1": "NT 11"},
    }
    assert nt.table.rows == [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]
    assert nt.table

    assert na is not None
    assert na.attributes.pairs == {"na0": "NA 0", "na1": "NA 1"}
    assert not na.table

    assert ta is not None
    assert ta.attributes.pairs == {"ta0": "TA 0", "ta1": "TA 1"}
    assert ta.table.rows_by_ident == {
        ("TA 00",): {"ta0": "TA 00", "ta1": "TA 01"},
        ("TA 10",): {"ta0": "TA 10", "ta1": "TA 11"},
    }
    assert ta.table.rows == [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]
    assert ta.table

    assert root
    assert root.count_entries() == 12


def test_add_node() -> None:
    root = _create_filled_tree().tree

    orig_node = StructuredDataNode()
    orig_node.attributes.add_pairs({"sn0": "SN 0", "sn1": "SN 1"})
    orig_node.table.add_key_columns(["sn0"])
    orig_node.table.add_rows(
        [
            {"sn0": "SN 00", "sn1": "SN 01"},
            {"sn0": "SN 10", "sn1": "SN 11"},
        ]
    )

    root.add_node(("path-to", "nta", "node"), orig_node)
    node = root.get_node(("path-to", "nta", "node"))
    assert node is not None

    # Do not modify orig node.
    assert orig_node.path == tuple()

    assert node.table.key_columns == ["sn0"]
    assert node.path == ("path-to", "nta", "node")

    assert root
    assert root.count_entries() == 18


def test_compare_trees_self_1() -> None:
    empty_root = _create_empty_tree()
    delta_tree0 = empty_root.difference(empty_root).tree
    delta_result0 = delta_tree0.count_entries()
    assert delta_result0["new"] == 0
    assert delta_result0["changed"] == 0
    assert delta_result0["removed"] == 0
    assert not delta_tree0

    filled_root = _create_filled_tree()
    delta_tree1 = filled_root.difference(filled_root).tree
    delta_result1 = delta_tree1.count_entries()
    assert delta_result1["new"] == 0
    assert delta_result1["changed"] == 0
    assert delta_result1["removed"] == 0
    assert not delta_tree1


def test_compare_trees_1() -> None:
    # Results must be symmetric
    empty_root = _create_empty_tree()
    filled_root = _create_filled_tree()

    delta_tree0 = empty_root.difference(filled_root).tree
    delta_result0 = delta_tree0.count_entries()
    assert delta_result0["new"] == 0
    assert delta_result0["changed"] == 0
    assert delta_result0["removed"] == 12

    delta_tree1 = filled_root.difference(empty_root).tree
    delta_result1 = delta_tree1.count_entries()
    assert delta_result1["new"] == 12
    assert delta_result1["changed"] == 0
    assert delta_result1["removed"] == 0

    assert not ImmutableDeltaTree(delta_tree1).filter([])


def test_filter_delta_tree_nt() -> None:
    filtered = (
        _create_filled_tree()
        .difference(_create_empty_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to", "nta", "nt"),
                    filter_nodes=lambda n: False,
                    filter_attributes=lambda k: k in ["nt1"],
                    filter_columns=lambda k: k in ["nt1"],
                )
            ],
        )
    ).tree

    assert filtered.get_node(("path-to", "nta", "na")) is None
    assert filtered.get_node(("path-to", "nta", "ta")) is None

    filtered_child = filtered.get_node(("path-to", "nta", "nt"))
    assert filtered_child is not None
    assert filtered_child.path == ("path-to", "nta", "nt")
    assert filtered_child.attributes.pairs == {}
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"nt1": (None, "NT 01")},
        {"nt1": (None, "NT 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_na() -> None:
    filtered = (
        _create_filled_tree()
        .difference(_create_empty_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to", "nta", "na"),
                    filter_nodes=lambda n: False,
                    filter_attributes=lambda k: k in ["na1"],
                    filter_columns=lambda k: k in ["na1"],
                )
            ],
        )
    ).tree

    assert filtered.get_node(("path-to", "nta", "nt")) is None
    assert filtered.get_node(("path-to", "nta", "ta")) is None

    filtered_child = filtered.get_node(("path-to", "nta", "na"))
    assert filtered_child is not None
    assert filtered_child.path == ("path-to", "nta", "na")
    assert filtered_child.attributes.pairs == {"na1": (None, "NA 1")}
    assert filtered_child.table.rows == []


def test_filter_delta_tree_ta() -> None:
    filtered = (
        _create_filled_tree()
        .difference(_create_empty_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to", "nta", "ta"),
                    filter_nodes=lambda n: False,
                    filter_attributes=lambda k: k in ["ta1"],
                    filter_columns=lambda k: k in ["ta1"],
                )
            ],
        )
        .tree
    )

    assert filtered.get_node(("path-to", "nta", "nt")) is None
    assert filtered.get_node(("path-to", "nta", "na")) is None

    filtered_child = filtered.get_node(("path-to", "nta", "ta"))
    assert filtered_child is not None
    assert filtered_child.path == ("path-to", "nta", "ta")
    assert filtered_child.attributes.pairs == {"ta1": (None, "TA 1")}
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"ta1": (None, "TA 01")},
        {"ta1": (None, "TA 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_nta_ta() -> None:
    filtered = (
        _create_filled_tree()
        .difference(_create_empty_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to", "nta", "ta"),
                    filter_nodes=lambda n: False,
                    filter_attributes=lambda k: k in ["ta0"],
                    filter_columns=lambda k: k in ["ta0"],
                ),
                SDFilter(
                    path=("path-to", "nta", "ta"),
                    filter_nodes=lambda n: False,
                    filter_attributes=lambda k: k in ["ta1"],
                    filter_columns=lambda k: k in ["ta1"],
                ),
            ],
        )
        .tree
    )

    assert filtered.get_node(("path-to", "nta", "nt")) is None
    assert filtered.get_node(("path-to", "nta", "na")) is None
    assert filtered.get_node(("path-to", "nta", "ta")) is not None

    filtered_ta = filtered.get_node(("path-to", "nta", "ta"))
    assert filtered_ta is not None
    assert filtered_ta.attributes.pairs == {"ta0": (None, "TA 0"), "ta1": (None, "TA 1")}
    assert len(filtered_ta.table.rows) == 4
    for row in (
        {"ta0": (None, "TA 00")},
        {"ta0": (None, "TA 10")},
        {"ta1": (None, "TA 01")},
        {"ta1": (None, "TA 11")},
    ):
        assert row in filtered_ta.table.rows


@pytest.mark.parametrize(
    "old_attributes_data, new_attributes_data, result",
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
def test__compare_attributes(
    old_attributes_data: Mapping[str, str],
    new_attributes_data: Mapping[str, str],
    result: tuple[int, int, int],
) -> None:
    old_attributes = Attributes()
    old_attributes.add_pairs(old_attributes_data)

    new_attributes = Attributes()
    new_attributes.add_pairs(new_attributes_data)

    delta_result = _compare_attributes(new_attributes, old_attributes).count_entries()
    assert (
        delta_result["new"],
        delta_result["changed"],
        delta_result["removed"],
    ) == result


@pytest.mark.parametrize(
    "old_table_data, new_table_data, result",
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
def test__compare_tables(
    old_table_data: Sequence[Mapping[str, str | int]],
    new_table_data: Sequence[Mapping[str, str | int]],
    result: tuple[int, int, int],
) -> None:
    old_table = Table(key_columns=["id"])
    old_table.add_rows(old_table_data)
    new_table = Table(key_columns=["id"])
    new_table.add_rows(new_table_data)

    delta_table = _compare_tables(new_table, old_table)
    if any(result):
        assert delta_table
    else:
        assert not delta_table

    delta_result = delta_table.count_entries()
    assert (
        delta_result["new"],
        delta_result["changed"],
        delta_result["removed"],
    ) == result


@pytest.mark.parametrize(
    "old_row, new_row, expected_keys",
    [
        ({}, {}, set()),
        ({"id": "id", "val": "val"}, {"id": "id", "val": "val"}, set()),
        ({"id": "id", "val": "val"}, {"id": "id"}, {"id", "val"}),
        ({"id": "id"}, {"id": "id", "val": "val"}, {"id", "val"}),
        ({"id": "id1", "val": "val"}, {"id": "id2", "val": "val"}, {"id", "val"}),
    ],
)
def test__compare_tables_row_keys(
    old_row: dict[str, str],
    new_row: dict[str, str],
    expected_keys: set[str],
) -> None:
    old_table = Table(key_columns=["id"])
    old_table.add_rows([old_row])
    new_table = Table(key_columns=["id"])
    new_table.add_rows([new_row])

    delta_table = _compare_tables(new_table, old_table)
    assert {k for r in delta_table.rows for k in r} == expected_keys


def test_filter_tree_no_paths() -> None:
    filled_root = _create_filled_tree()
    assert not filled_root.filter([])


def test_filter_tree_wrong_node() -> None:
    filled_root = _create_filled_tree()
    filters = [
        SDFilter(
            path=("path-to", "nta", "ta"),
            filter_nodes=lambda k: True,
            filter_attributes=lambda k: True,
            filter_columns=lambda k: True,
        ),
    ]
    filtered = filled_root.filter(filters).tree
    assert filtered.get_node(("path-to", "nta", "na")) is None
    assert filtered.get_node(("path-to", "nta", "nt")) is None


def test_filter_tree_paths_no_keys() -> None:
    filled_root = _create_filled_tree()
    filters = [
        SDFilter(
            path=("path-to", "nta", "ta"),
            filter_nodes=lambda k: True,
            filter_attributes=lambda k: True,
            filter_columns=lambda k: True,
        ),
    ]
    filtered_node = filled_root.filter(filters).tree.get_node(("path-to", "nta", "ta"))
    assert filtered_node is not None

    assert filtered_node.attributes
    assert filtered_node.attributes.pairs == {"ta0": "TA 0", "ta1": "TA 1"}

    assert bool(filtered_node.table)
    assert len(filtered_node.table.rows_by_ident) == 2
    for ident, row in {
        ("TA 00",): {"ta0": "TA 00", "ta1": "TA 01"},
        ("TA 10",): {"ta0": "TA 10", "ta1": "TA 11"},
    }.items():
        assert filtered_node.table.rows_by_ident[ident] == row


def test_filter_tree_paths_and_keys() -> None:
    filled_root = _create_filled_tree()
    filters = [
        SDFilter(
            path=("path-to", "nta", "ta"),
            filter_nodes=lambda k: True,
            filter_attributes=lambda k: k in ["ta1"],
            filter_columns=lambda k: k in ["ta1"],
        ),
    ]
    filtered_node = filled_root.filter(filters).tree.get_node(("path-to", "nta", "ta"))
    assert filtered_node is not None

    assert filtered_node.attributes
    assert filtered_node.attributes.pairs == {"ta1": "TA 1"}

    assert bool(filtered_node.table)
    for ident, row in {
        ("TA 00",): {"ta1": "TA 01"},
        ("TA 10",): {"ta1": "TA 11"},
    }.items():
        assert filtered_node.table.rows_by_ident[ident] == row


def test_filter_tree_mixed() -> None:
    filled_root = _create_filled_tree().tree
    another_node1 = filled_root.setdefault_node(("path-to", "another", "node1"))
    another_node1.attributes.add_pairs({"ak11": "Another value 11", "ak12": "Another value 12"})

    another_node2 = filled_root.setdefault_node(("path-to", "another", "node2"))
    another_node2.table.add_key_columns(["ak21"])
    another_node2.table.add_rows(
        [
            {
                "ak21": "Another value 211",
                "ak22": "Another value 212",
            },
            {
                "ak21": "Another value 221",
                "ak22": "Another value 222",
            },
        ]
    )

    filters = [
        SDFilter(
            path=("path-to", "another"),
            filter_nodes=lambda k: True,
            filter_attributes=lambda k: True,
            filter_columns=lambda k: True,
        ),
        SDFilter(
            path=("path-to", "nta", "ta"),
            filter_nodes=lambda k: True,
            filter_attributes=lambda k: k in ["ta0"],
            filter_columns=lambda k: k in ["ta0"],
        ),
    ]
    filtered_node = ImmutableTree(filled_root).filter(filters).tree

    # TODO 'serialize' only contains 8 entries because:
    # At the moment it's not possible to display attributes and table
    # below same node.
    assert filtered_node.count_entries() == 9

    assert filtered_node.get_node(("path-to", "nta", "nt")) is None
    assert filtered_node.get_node(("path-to", "nta", "na")) is None

    assert filtered_node.get_node(("path-to", "another", "node1")) is not None
    assert filtered_node.get_node(("path-to", "another", "node2")) is not None


# Tests with real host data


def _get_tree_store() -> TreeStore:
    return TreeStore(Path("%s/tests/unit/cmk/utils/structured_data/tree_test_data" % cmk_path()))


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
def test_structured_data_StructuredDataTree_load_from(tree_name: HostName) -> None:
    _get_tree_store().load(host_name=tree_name)


def test_real_save_gzip(tmp_path: Path) -> None:
    host_name = HostName("heute")
    target = tmp_path / "inventory" / str(host_name)
    tree = MutableTree()
    tree.add_pairs(path=["path-to", "node"], pairs={"foo": 1, "bär": 2})
    tree_store = TreeStore(tmp_path / "inventory")
    tree_store.save(host_name=host_name, tree=tree)

    assert target.exists()

    gzip_filepath = target.with_suffix(".gz")
    assert gzip_filepath.exists()

    with gzip.open(str(gzip_filepath), "rb") as f:
        f.read()


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
def test_real_is_empty_trees(tree_name: HostName) -> None:
    assert _get_tree_store().load(host_name=tree_name)


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
def test_real_is_equal(tree_name_x: HostName, tree_name_y: HostName) -> None:
    tree_store = _get_tree_store()
    tree_x = tree_store.load(host_name=tree_name_x)
    tree_y = tree_store.load(host_name=tree_name_y)

    if tree_name_x == tree_name_y:
        assert tree_x == tree_y
    else:
        assert tree_x != tree_y


def test_real_equal_tables() -> None:
    tree_store = _get_tree_store()
    tree_ordered = tree_store.load(host_name=HostName("tree_addresses_ordered"))
    tree_unordered = tree_store.load(host_name=HostName("tree_addresses_unordered"))
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
def test_real_is_equal_save_and_load(tree_name: HostName, tmp_path: Path) -> None:
    orig_tree = _get_tree_store().load(host_name=tree_name)
    tree_store = TreeStore(tmp_path / "inventory")
    try:
        tree_store.save(host_name=HostName("foo"), tree=MutableTree(orig_tree.tree))
        loaded_tree = tree_store.load(host_name=HostName("foo"))
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
def test_real_count_entries(tree_name: HostName, result: int) -> None:
    assert _get_tree_store().load(host_name=tree_name).tree.count_entries() == result


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
def test_compare_trees_self_2(tree_name: HostName) -> None:
    tree = _get_tree_store().load(host_name=tree_name)
    delta_result = tree.difference(tree).tree.count_entries()
    assert (
        delta_result["new"],
        delta_result["changed"],
        delta_result["removed"],
    ) == (0, 0, 0)


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
def test_compare_trees_2(
    tree_name_old: HostName, tree_name_new: HostName, result: tuple[int, int, int]
) -> None:
    tree_store = _get_tree_store()
    old_tree = tree_store.load(host_name=tree_name_old)
    new_tree = tree_store.load(host_name=tree_name_new)
    delta_result = new_tree.difference(old_tree).tree.count_entries()
    assert (
        delta_result["new"],
        delta_result["changed"],
        delta_result["removed"],
    ) == result


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
def test_real_get_node(
    tree_name: HostName, edges_t: Iterable[SDNodeName], edges_f: Iterable[SDNodeName]
) -> None:
    tree = _get_tree_store().load(host_name=tree_name)
    for edge_t in edges_t:
        assert tree.tree.get_node((edge_t,)) is not None
    for edge_f in edges_f:
        assert tree.tree.get_node((edge_f,)) is None


@pytest.mark.parametrize(
    "tree_name, len_children",
    [
        (HostName("tree_old_addresses_arrays_memory"), 2),
        (HostName("tree_old_addresses"), 1),
        (HostName("tree_old_arrays"), 1),
        (HostName("tree_old_interfaces"), 3),
        (HostName("tree_old_memory"), 1),
        (HostName("tree_old_heute"), 3),
    ],
)
def test_real_get_children(tree_name: HostName, len_children: int) -> None:
    tree = _get_tree_store().load(host_name=tree_name)
    tree_children = tree.tree._nodes
    assert len(tree_children) == len_children


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
    tree_store = _get_tree_store()

    tree = (
        tree_store.load(host_name=HostName("tree_old_addresses"))
        .merge(tree_store.load(host_name=tree_name))
        .tree
    )

    assert id(tree) == id(tree)
    for edge in edges:
        assert tree.get_node((edge,)) is not None

    for m_name, path in sub_children:
        m = getattr(tree, m_name)
        assert m is not None
        assert m(path) is not None


def test_merge_trees_2() -> None:
    tree_store = _get_tree_store()
    inventory_tree = tree_store.load(host_name=HostName("tree_inv"))
    status_data_tree = tree_store.load(host_name=HostName("tree_status"))
    tree = inventory_tree.merge(status_data_tree).tree
    assert "foobar" in tree.serialize()["Nodes"]
    table = tree.get_table(("foobar",))
    assert table is not None
    assert len(table.rows) == 5


@pytest.mark.parametrize(
    "filters, unavail",
    [
        (
            # container                   table                    attributes
            [
                SDFilter(
                    path=("hardware", "components"),
                    filter_nodes=lambda k: True,
                    filter_attributes=lambda k: True,
                    filter_columns=lambda k: True,
                ),
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_nodes=lambda k: True,
                    filter_attributes=lambda k: True,
                    filter_columns=lambda k: True,
                ),
                SDFilter(
                    path=("software", "os"),
                    filter_nodes=lambda k: True,
                    filter_attributes=lambda k: True,
                    filter_columns=lambda k: True,
                ),
            ],
            [("hardware", "system"), ("software", "applications")],
        ),
    ],
)
def test_real_filtered_tree(
    filters: Sequence[SDFilter],
    unavail: Sequence[tuple[str, str]],
) -> None:
    tree = _get_tree_store().load(host_name=HostName("tree_new_interfaces"))
    filtered = tree.filter(filters)
    assert id(tree) != id(filtered)
    assert tree != filtered
    for path in unavail:
        assert filtered.tree.get_node(path) is None


@pytest.mark.parametrize(
    "filters, amount_if_entries",
    [
        (
            [
                SDFilter(
                    path=("networking",),
                    filter_nodes=lambda k: True,
                    filter_attributes=lambda k: True,
                    filter_columns=lambda k: True,
                )
            ],
            3178,
        ),
        (
            [
                SDFilter(
                    path=("networking",),
                    filter_nodes=lambda k: False,
                    filter_attributes=lambda k: False,
                    filter_columns=lambda k: False,
                ),
            ],
            None,
        ),
        (
            [
                SDFilter(
                    path=("networking",),
                    filter_nodes=lambda k: False,
                    filter_attributes=(
                        lambda k: k
                        in ["total_interfaces", "total_ethernet_ports", "available_ethernet_ports"]
                    ),
                    filter_columns=(
                        lambda k: k
                        in ["total_interfaces", "total_ethernet_ports", "available_ethernet_ports"]
                    ),
                ),
            ],
            None,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_nodes=lambda k: True,
                    filter_attributes=lambda k: True,
                    filter_columns=lambda k: True,
                ),
            ],
            3178,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_nodes=lambda k: False,
                    filter_attributes=lambda k: k in ["admin_status"],
                    filter_columns=lambda k: k in ["admin_status"],
                ),
            ],
            326,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_nodes=lambda k: False,
                    filter_attributes=lambda k: k in ["admin_status", "FOOBAR"],
                    filter_columns=lambda k: k in ["admin_status", "FOOBAR"],
                ),
            ],
            326,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_nodes=lambda k: False,
                    filter_attributes=lambda k: k in ["admin_status", "oper_status"],
                    filter_columns=lambda k: k in ["admin_status", "oper_status"],
                ),
            ],
            652,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_nodes=lambda k: False,
                    filter_attributes=lambda k: k in ["admin_status", "oper_status", "FOOBAR"],
                    filter_columns=lambda k: k in ["admin_status", "oper_status", "FOOBAR"],
                ),
            ],
            652,
        ),
    ],
)
def test_real_filtered_tree_networking(
    filters: Sequence[SDFilter],
    amount_if_entries: int,
) -> None:
    tree = _get_tree_store().load(host_name=HostName("tree_new_interfaces"))
    filtered = tree.filter(filters).tree
    assert filtered.get_node(("networking",)) is not None
    assert filtered.get_node(("hardware",)) is None
    assert filtered.get_node(("software",)) is None

    if amount_if_entries is not None:
        interfaces = filtered.get_table(
            (
                "networking",
                "interfaces",
            )
        )
        assert interfaces is not None
        assert interfaces.count_entries() == amount_if_entries


@pytest.mark.parametrize(
    "tree_name_old, tree_name_new",
    [
        (
            HostName("tree_old_addresses_arrays_memory"),
            HostName("tree_new_addresses_arrays_memory"),
        ),
        (
            HostName("tree_old_addresses"),
            HostName("tree_new_addresses"),
        ),
        (
            HostName("tree_old_arrays"),
            HostName("tree_new_arrays"),
        ),
        (
            HostName("tree_old_interfaces"),
            HostName("tree_new_interfaces"),
        ),
        (
            HostName("tree_old_memory"),
            HostName("tree_new_memory"),
        ),
        (
            HostName("tree_old_heute"),
            HostName("tree_new_heute"),
        ),
    ],
)
def test_delta_structured_data_tree_serialization(
    tree_name_old: HostName,
    tree_name_new: HostName,
) -> None:
    tree_store = _get_tree_store()

    previous_tree = tree_store.load(host_name=tree_name_old)
    inventory_tree = tree_store.load(host_name=tree_name_new)
    delta_tree = previous_tree.difference(inventory_tree).tree

    delta_raw_tree = delta_tree.serialize()
    assert isinstance(delta_raw_tree, dict)

    ImmutableDeltaTree.deserialize(delta_raw_tree)


@pytest.mark.parametrize(
    "raw_path, expected_path",
    [
        ("", tuple()),
        ("path-to.node_1", ("path-to", "node_1")),
    ],
)
def test_parse_visible_tree_path(raw_path: str, expected_path: SDPath) -> None:
    assert parse_visible_raw_path(raw_path) == expected_path


def test__is_table() -> None:
    raw_tree = {
        "path-to": {
            "idx-node": [
                {
                    "idx-attr": "value",
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

    tree = ImmutableTree.deserialize(raw_tree).tree

    idx_node_attr = tree.get_node(("path-to", "idx-node", "0"))
    assert idx_node_attr is not None
    assert idx_node_attr.attributes.pairs == {"idx-attr": "value"}
    assert idx_node_attr.table.rows_by_ident == {}
    assert idx_node_attr.table.rows == []

    idx_sub_idx_node_attr = tree.get_node(
        ("path-to", "idx-node", "0", "idx-sub-idx-node", "0", "bar-node")
    )
    assert idx_sub_idx_node_attr is not None
    assert idx_sub_idx_node_attr.attributes.pairs == {"bar-attr": "value"}
    assert idx_sub_idx_node_attr.table.rows_by_ident == {}
    assert idx_sub_idx_node_attr.table.rows == []

    idx_sub_node_attr = tree.get_node(("path-to", "idx-node", "0", "idx-sub-node", "foo-node"))
    assert idx_sub_node_attr is not None
    assert idx_sub_node_attr.attributes.pairs == {"foo-attr": "value"}
    assert idx_sub_node_attr.table.rows_by_ident == {}
    assert idx_sub_node_attr.table.rows == []

    idx_table = tree.get_node(("path-to", "idx-node", "0", "idx-table"))
    assert idx_table is not None
    assert idx_table.attributes.pairs == {}
    assert idx_table.table.rows_by_ident == {("value",): {"idx-col": "value"}}
    assert idx_table.table.rows == [{"idx-col": "value"}]

    attr_node = tree.get_node(("path-to", "node"))
    assert attr_node is not None
    assert attr_node.attributes.pairs == {"attr": "value"}
    assert attr_node.table.rows_by_ident == {}
    assert attr_node.table.rows == []

    table_node = tree.get_node(("path-to", "table"))
    assert table_node is not None
    assert table_node.attributes.pairs == {}
    assert table_node.table.rows_by_ident == {("value",): {"col": "value"}}
    assert table_node.table.rows == [{"col": "value"}]


def test_table_update_from_previous() -> None:
    previous_table = Table(
        key_columns=["kc"],
        retentions={
            ("KC",): {
                "c1": RetentionIntervals(1, 2, 3),
                "c2": RetentionIntervals(1, 2, 3),
            }
        },
    )
    previous_table.add_rows([{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}])

    current_table = Table(key_columns=["kc"])
    current_table.add_rows([{"kc": "KC", "c1": "C1: cur", "c3": "C3: only cur"}])

    current_table.update_from_previous(
        0,
        ("any", "path"),
        previous_table,
        lambda k: True,
        RetentionIntervals(4, 5, 6),
    )

    assert current_table.key_columns == ["kc"]
    assert current_table.retentions == {
        ("KC",): {
            "c1": RetentionIntervals(4, 5, 6),
            "c2": RetentionIntervals(1, 2, 3),
            "c3": RetentionIntervals(4, 5, 6),
            "kc": RetentionIntervals(4, 5, 6),
        }
    }
    assert current_table.rows == [
        {"c1": "C1: cur", "c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}
    ]


def test_table_update_from_previous_filtered() -> None:
    previous_table = Table(
        key_columns=["kc"],
        retentions={
            ("KC",): {
                "c1": RetentionIntervals(1, 2, 3),
                "c2": RetentionIntervals(1, 2, 3),
            }
        },
    )
    previous_table.add_rows([{"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"}])
    current_table = Table(key_columns=["kc"])
    current_table.add_rows([{"kc": "KC", "c3": "C3: only cur"}])
    current_table.update_from_previous(
        0,
        ("any", "path"),
        previous_table,
        lambda k: k in ["c2", "c3"],
        RetentionIntervals(4, 5, 6),
    )
    assert current_table.key_columns == ["kc"]
    assert current_table.retentions == {
        ("KC",): {
            "c2": RetentionIntervals(1, 2, 3),
            "c3": RetentionIntervals(4, 5, 6),
        }
    }
    assert current_table.rows == [{"c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}]
