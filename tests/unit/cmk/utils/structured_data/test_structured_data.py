#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.testlib import cmk_path

from cmk.utils.structured_data import (
    Attributes,
    DeltaStructuredDataNode,
    filter_delta_tree,
    make_filter,
    parse_visible_raw_path,
    RetentionIntervals,
    SDFilter,
    SDNodeName,
    StructuredDataNode,
    Table,
    TableRetentions,
    TreeStore,
)
from cmk.utils.type_defs import HostName


def _make_filters(allowed_paths):
    return [make_filter(entry) for entry in allowed_paths]


# Test basic methods of StructuredDataNode, Table, Attributes


def _create_empty_tree():
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes

    root = StructuredDataNode()

    root.setdefault_node(("path", "to", "nta", "nt"))
    root.setdefault_node(("path", "to", "nta", "na"))
    root.setdefault_node(("path", "to", "nta", "ta"))

    return root


def _create_filled_tree():
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes

    root = StructuredDataNode()

    nt = root.setdefault_node(("path", "to", "nta", "nt"))
    na = root.setdefault_node(("path", "to", "nta", "na"))
    ta = root.setdefault_node(("path", "to", "nta", "ta"))

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

    return root


def test_get_node() -> None:
    root = _create_empty_tree()

    nta = root.get_node(("path", "to", "nta"))
    nt = root.get_node(("path", "to", "nta", "nt"))
    na = root.get_node(("path", "to", "nta", "na"))
    ta = root.get_node(("path", "to", "nta", "ta"))

    assert nta is not None
    assert nt is not None
    assert na is not None
    assert ta is not None

    assert root.get_node(["path", "to", "unknown"]) is None


def test_set_path() -> None:
    root = _create_empty_tree()

    nta = root.get_node(("path", "to", "nta"))
    nt = root.get_node(("path", "to", "nta", "nt"))
    na = root.get_node(("path", "to", "nta", "na"))
    ta = root.get_node(("path", "to", "nta", "ta"))

    assert nta.attributes.path == ("path", "to", "nta")
    assert nta.table.path == ("path", "to", "nta")
    assert nta.path == ("path", "to", "nta")

    assert nt.attributes.path == ("path", "to", "nta", "nt")
    assert nt.table.path == ("path", "to", "nta", "nt")
    assert nt.path == ("path", "to", "nta", "nt")

    assert na.attributes.path == ("path", "to", "nta", "na")
    assert na.table.path == ("path", "to", "nta", "na")
    assert na.path == ("path", "to", "nta", "na")

    assert ta.attributes.path == ("path", "to", "nta", "ta")
    assert ta.table.path == ("path", "to", "nta", "ta")
    assert ta.path == ("path", "to", "nta", "ta")


def test_set_path_sub_nodes_error() -> None:
    root = _create_empty_tree()
    nta = root.get_node(("path", "to", "nta"))

    sub_node = StructuredDataNode()
    sub_node.setdefault_node(("sub-path", "sub-to", "sub-node"))

    with pytest.raises(ValueError):
        nta.add_node(sub_node)


def test_set_path_sub_nodes() -> None:
    root = _create_empty_tree()
    nta = root.get_node(("path", "to", "nta"))

    sub_node = StructuredDataNode(name="node")
    sub_node.setdefault_node(("sub-path-to", "sub-node"))

    nta.add_node(sub_node)

    path_to_node = root.get_node(["path", "to", "nta", "node", "sub-path-to"])
    assert path_to_node is not None
    assert path_to_node.attributes.path == ("path", "to", "nta", "node", "sub-path-to")
    assert path_to_node.table.path == ("path", "to", "nta", "node", "sub-path-to")
    assert path_to_node.path == ("path", "to", "nta", "node", "sub-path-to")

    path_to_sub_node = root.get_node(["path", "to", "nta", "node", "sub-path-to", "sub-node"])
    assert path_to_sub_node is not None
    assert path_to_sub_node.attributes.path == (
        "path",
        "to",
        "nta",
        "node",
        "sub-path-to",
        "sub-node",
    )
    assert path_to_sub_node.table.path == ("path", "to", "nta", "node", "sub-path-to", "sub-node")
    assert path_to_sub_node.path == ("path", "to", "nta", "node", "sub-path-to", "sub-node")


def test_empty_but_different_structure() -> None:
    root = _create_empty_tree()

    nt = root.get_node(["path", "to", "nta", "nt"])
    na = root.get_node(["path", "to", "nta", "na"])
    ta = root.get_node(["path", "to", "nta", "ta"])

    assert nt.attributes.pairs == {}
    assert nt.attributes.is_empty()
    assert nt.table._rows == {}
    assert nt.table.rows == []
    assert nt.table.is_empty()

    assert na.attributes.pairs == {}
    assert na.attributes.is_empty()
    assert na.table._rows == {}
    assert na.table.rows == []
    assert na.table.is_empty()

    assert ta.attributes.pairs == {}
    assert ta.attributes.is_empty()
    assert ta.table._rows == {}
    assert ta.table.rows == []
    assert ta.table.is_empty()

    assert root.is_empty()
    assert root.count_entries() == 0
    assert not root.is_equal(StructuredDataNode())


def test_not_empty() -> None:
    root = _create_filled_tree()

    nt = root.get_node(["path", "to", "nta", "nt"])
    na = root.get_node(["path", "to", "nta", "na"])
    ta = root.get_node(["path", "to", "nta", "ta"])

    assert nt.attributes.pairs == {}
    assert nt.attributes.is_empty()
    assert nt.table._rows == {
        ("NT 00",): {"nt0": "NT 00", "nt1": "NT 01"},
        ("NT 10",): {"nt0": "NT 10", "nt1": "NT 11"},
    }
    assert nt.table.rows == [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]
    assert not nt.table.is_empty()

    assert na.attributes.pairs == {"na0": "NA 0", "na1": "NA 1"}
    assert not na.attributes.is_empty()
    assert na.table._rows == {}
    assert na.table.rows == []
    assert na.table.is_empty()

    assert ta.attributes.pairs == {"ta0": "TA 0", "ta1": "TA 1"}
    assert not ta.attributes.is_empty()
    assert ta.table._rows == {
        ("TA 00",): {"ta0": "TA 00", "ta1": "TA 01"},
        ("TA 10",): {"ta0": "TA 10", "ta1": "TA 11"},
    }
    assert ta.table.rows == [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]
    assert not ta.table.is_empty()

    assert not root.is_empty()
    assert root.count_entries() == 12


def test_add_node() -> None:
    root = _create_filled_tree()

    sub_node = StructuredDataNode(name="node")
    sub_node.attributes.add_pairs({"sn0": "SN 0", "sn1": "SN 1"})

    sub_node.table.add_key_columns(["sn0"])
    sub_node.table.add_rows(
        [
            {"sn0": "SN 00", "sn1": "SN 01"},
            {"sn0": "SN 10", "sn1": "SN 11"},
        ]
    )

    node = root.get_node(["path", "to", "nta"]).add_node(sub_node)

    # Do not modify orig node.
    assert sub_node.attributes.path == tuple()
    assert sub_node.table.path == tuple()
    assert sub_node.path == tuple()

    assert node.attributes.path == tuple(["path", "to", "nta", "node"])

    assert node.table.key_columns == ["sn0"]
    assert node.table.path == ("path", "to", "nta", "node")
    assert node.path == ("path", "to", "nta", "node")

    assert not root.is_empty()
    assert root.count_entries() == 18


def test_compare_with_self() -> None:
    empty_root = _create_empty_tree()
    delta_tree0 = empty_root.compare_with(empty_root)
    delta_result0 = delta_tree0.count_entries()
    assert delta_result0["new"] == 0
    assert delta_result0["changed"] == 0
    assert delta_result0["removed"] == 0
    assert delta_tree0.is_empty()

    filled_root = _create_filled_tree()
    delta_tree1 = filled_root.compare_with(filled_root)
    delta_result1 = delta_tree1.count_entries()
    assert delta_result1["new"] == 0
    assert delta_result1["changed"] == 0
    assert delta_result1["removed"] == 0
    assert delta_tree1.is_empty()


def test_compare_with() -> None:
    # Results must be symmetric
    empty_root = _create_empty_tree()
    filled_root = _create_filled_tree()

    delta_tree0 = empty_root.compare_with(filled_root)
    delta_result0 = delta_tree0.count_entries()
    assert delta_result0["new"] == 0
    assert delta_result0["changed"] == 0
    assert delta_result0["removed"] == 12

    delta_tree1 = filled_root.compare_with(empty_root)
    delta_result1 = delta_tree1.count_entries()
    assert delta_result1["new"] == 12
    assert delta_result1["changed"] == 0
    assert delta_result1["removed"] == 0

    assert filter_delta_tree(delta_tree1, []).is_empty()


def test_filter_delta_tree_nt() -> None:
    filtered = filter_delta_tree(
        _create_filled_tree().compare_with(_create_empty_tree()),
        [
            SDFilter(
                path=("path", "to", "nta", "nt"),
                filter_nodes=lambda n: False,
                filter_attributes=lambda k: k in ["nt1"],
                filter_columns=lambda k: k in ["nt1"],
            )
        ],
    )

    assert filtered.get_node(("path", "to", "nta", "na")) is None
    assert filtered.get_node(("path", "to", "nta", "ta")) is None

    filtered_child = filtered.get_node(("path", "to", "nta", "nt"))
    assert filtered_child is not None
    assert filtered_child.path == ("path", "to", "nta", "nt")
    assert filtered_child.attributes.path == ("path", "to", "nta", "nt")
    assert filtered_child.table.path == ("path", "to", "nta", "nt")
    assert filtered_child.attributes.pairs == {}
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"nt1": (None, "NT 01")},
        {"nt1": (None, "NT 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_na() -> None:
    filtered = filter_delta_tree(
        _create_filled_tree().compare_with(_create_empty_tree()),
        [
            SDFilter(
                path=("path", "to", "nta", "na"),
                filter_nodes=lambda n: False,
                filter_attributes=lambda k: k in ["na1"],
                filter_columns=lambda k: k in ["na1"],
            )
        ],
    )

    assert filtered.get_node(("path", "to", "nta", "nt")) is None
    assert filtered.get_node(("path", "to", "nta", "ta")) is None

    filtered_child = filtered.get_node(("path", "to", "nta", "na"))
    assert filtered_child is not None
    assert filtered_child.path == ("path", "to", "nta", "na")
    assert filtered_child.attributes.path == ("path", "to", "nta", "na")
    assert filtered_child.table.path == ("path", "to", "nta", "na")
    assert filtered_child.attributes.pairs == {"na1": (None, "NA 1")}
    assert filtered_child.table.rows == []


def test_filter_delta_tree_ta() -> None:
    filtered = filter_delta_tree(
        _create_filled_tree().compare_with(_create_empty_tree()),
        [
            SDFilter(
                path=("path", "to", "nta", "ta"),
                filter_nodes=lambda n: False,
                filter_attributes=lambda k: k in ["ta1"],
                filter_columns=lambda k: k in ["ta1"],
            )
        ],
    )

    assert filtered.get_node(("path", "to", "nta", "nt")) is None
    assert filtered.get_node(("path", "to", "nta", "na")) is None

    filtered_child = filtered.get_node(("path", "to", "nta", "ta"))
    assert filtered_child is not None
    assert filtered_child.path == ("path", "to", "nta", "ta")
    assert filtered_child.attributes.path == ("path", "to", "nta", "ta")
    assert filtered_child.table.path == ("path", "to", "nta", "ta")
    assert filtered_child.attributes.pairs == {"ta1": (None, "TA 1")}
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"ta1": (None, "TA 01")},
        {"ta1": (None, "TA 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_nta_ta() -> None:
    filtered = filter_delta_tree(
        _create_filled_tree().compare_with(_create_empty_tree()),
        [
            SDFilter(
                path=("path", "to", "nta", "ta"),
                filter_nodes=lambda n: False,
                filter_attributes=lambda k: k in ["ta0"],
                filter_columns=lambda k: k in ["ta0"],
            ),
            SDFilter(
                path=("path", "to", "nta", "ta"),
                filter_nodes=lambda n: False,
                filter_attributes=lambda k: k in ["ta1"],
                filter_columns=lambda k: k in ["ta1"],
            ),
        ],
    )

    assert filtered.get_node(("path", "to", "nta", "nt")) is None
    assert filtered.get_node(("path", "to", "nta", "na")) is None
    assert filtered.get_node(("path", "to", "nta", "ta")) is not None

    filtered_ta = filtered.get_node(("path", "to", "nta", "ta"))
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
def test_attributes_compare_with(
    old_attributes_data: Mapping[str, str],
    new_attributes_data: Mapping[str, str],
    result: tuple[int, int, int],
) -> None:
    old_attributes = Attributes()
    old_attributes.add_pairs(old_attributes_data)

    new_attributes = Attributes()
    new_attributes.add_pairs(new_attributes_data)

    delta_result = new_attributes.compare_with(old_attributes).count_entries()
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
def test_table_compare_with(
    old_table_data: Iterable[dict[str, str | int]],
    new_table_data: Iterable[dict[str, str | int]],
    result: tuple[int, int, int],
) -> None:
    old_table = Table(key_columns=["id"])
    old_table.add_rows(old_table_data)
    new_table = Table(key_columns=["id"])
    new_table.add_rows(new_table_data)

    delta_table = new_table.compare_with(old_table)
    if any(result):
        assert not delta_table.is_empty()
    else:
        assert delta_table.is_empty()

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
        ({"id": "id", "val": "val"}, {"id": "id"}, set(["id", "val"])),
        ({"id": "id"}, {"id": "id", "val": "val"}, set(["id", "val"])),
        ({"id": "id1", "val": "val"}, {"id": "id2", "val": "val"}, set(["id", "val"])),
    ],
)
def test_table_row_keys_compare_with(
    old_row: dict[str, str],
    new_row: dict[str, str],
    expected_keys: set[str],
) -> None:
    old_table = Table(key_columns=["id"])
    old_table.add_rows([old_row])
    new_table = Table(key_columns=["id"])
    new_table.add_rows([new_row])

    delta_table = new_table.compare_with(old_table)
    assert set(k for r in delta_table.rows for k in r) == expected_keys


def test_filtering_node_no_paths() -> None:
    filled_root = _create_filled_tree()
    assert filled_root.get_filtered_node([]).is_empty()


def test_filtering_node_wrong_node() -> None:
    filled_root = _create_filled_tree()
    filters = _make_filters([(("path", "to", "nta", "ta"), None)])
    filtered = filled_root.get_filtered_node(filters)
    assert filtered.get_node(["path", "to", "nta", "na"]) is None
    assert filtered.get_node(["path", "to", "nta", "nt"]) is None


def test_filtering_node_paths_no_keys() -> None:
    filled_root = _create_filled_tree()
    filters = _make_filters([(("path", "to", "nta", "ta"), None)])
    filtered_node = filled_root.get_filtered_node(filters).get_node(["path", "to", "nta", "ta"])
    assert filtered_node is not None
    assert filtered_node.name == "ta"
    assert filtered_node.path == ("path", "to", "nta", "ta")

    assert not filtered_node.attributes.is_empty()
    assert filtered_node.attributes.pairs == {"ta0": "TA 0", "ta1": "TA 1"}

    assert not filtered_node.table.is_empty()
    assert filtered_node.table._rows == {
        ("TA 00",): {"ta0": "TA 00", "ta1": "TA 01"},
        ("TA 10",): {"ta0": "TA 10", "ta1": "TA 11"},
    }
    assert filtered_node.table.rows == [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]


def test_filtering_node_paths_and_keys() -> None:
    filled_root = _create_filled_tree()
    filters = _make_filters([(("path", "to", "nta", "ta"), ["ta1"])])
    filtered_node = filled_root.get_filtered_node(filters).get_node(["path", "to", "nta", "ta"])
    assert filtered_node is not None

    assert not filtered_node.attributes.is_empty()
    assert filtered_node.attributes.pairs == {"ta1": "TA 1"}

    assert not filtered_node.table.is_empty()
    assert filtered_node.table._rows == {
        ("TA 00",): {
            "ta1": "TA 01",
        },
        ("TA 10",): {
            "ta1": "TA 11",
        },
    }
    assert filtered_node.table.rows == [
        {
            "ta1": "TA 01",
        },
        {
            "ta1": "TA 11",
        },
    ]


def test_filtering_node_mixed() -> None:
    filled_root = _create_filled_tree()
    another_node1 = filled_root.setdefault_node(["path", "to", "another", "node1"])
    another_node1.attributes.add_pairs({"ak11": "Another value 11", "ak12": "Another value 12"})

    another_node2 = filled_root.setdefault_node(["path", "to", "another", "node2"])
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

    filters = _make_filters(
        [
            (("path", "to", "another"), None),
            (("path", "to", "nta", "ta"), ["ta0"]),
        ]
    )
    filtered_node = filled_root.get_filtered_node(filters)

    # TODO 'serialize' only contains 8 entries because:
    # At the moment it's not possible to display attributes and table
    # below same node.
    assert filtered_node.count_entries() == 9

    assert filtered_node.get_node(["path", "to", "nta", "nt"]) is None
    assert filtered_node.get_node(["path", "to", "nta", "na"]) is None

    assert filtered_node.get_node(["path", "to", "another", "node1"]) is not None
    assert filtered_node.get_node(["path", "to", "another", "node2"]) is not None


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
    raw_tree = {
        "node": {
            "foo": 1,
            "bär": 2,
        },
    }
    tree = StructuredDataNode.deserialize(raw_tree)
    tree_store = TreeStore(tmp_path / "inventory")
    tree_store.save(host_name=host_name, tree=tree)

    assert target.exists()

    gzip_filepath = target.with_suffix(".gz")
    assert gzip_filepath.exists()

    with gzip.open(str(gzip_filepath), "rb") as f:
        f.read()


def test_real_is_empty() -> None:
    assert StructuredDataNode().is_empty() is True


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
    assert not _get_tree_store().load(host_name=tree_name).is_empty()


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
        assert tree_x.is_equal(tree_y)
    else:
        assert not tree_x.is_equal(tree_y)


def test_real_equal_tables() -> None:
    tree_store = _get_tree_store()
    tree_addresses_ordered = tree_store.load(host_name=HostName("tree_addresses_ordered"))
    tree_addresses_unordered = tree_store.load(host_name=HostName("tree_addresses_unordered"))

    assert tree_addresses_ordered.is_equal(tree_addresses_unordered)
    assert tree_addresses_unordered.is_equal(tree_addresses_ordered)


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
    tree = _get_tree_store().load(host_name=tree_name)
    tree_store = TreeStore(tmp_path / "inventory")
    try:
        tree_store.save(host_name=HostName("foo"), tree=tree)
        loaded_tree = tree_store.load(host_name=HostName("foo"))
        assert tree.is_equal(loaded_tree)
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
    assert _get_tree_store().load(host_name=tree_name).count_entries() == result


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
def test_real_compare_with_self(tree_name: HostName) -> None:
    tree = _get_tree_store().load(host_name=tree_name)
    delta_result = tree.compare_with(tree).count_entries()
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
def test_real_compare_with(
    tree_name_old: HostName, tree_name_new: HostName, result: tuple[int, int, int]
) -> None:
    tree_store = _get_tree_store()
    tree_old = tree_store.load(host_name=tree_name_old)
    tree_new = tree_store.load(host_name=tree_name_new)
    delta_result = tree_new.compare_with(tree_old).count_entries()
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
        assert tree.get_node((edge_t,)) is not None
    for edge_f in edges_f:
        assert tree.get_node((edge_f,)) is None


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
    tree_children = tree._nodes
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
def test_real_merge_with_get_children(
    tree_name: HostName, edges: Sequence[str], sub_children: Sequence[tuple[str, Sequence[str]]]
) -> None:
    tree_store = _get_tree_store()

    tree = tree_store.load(host_name=HostName("tree_old_addresses")).merge_with(
        tree_store.load(host_name=tree_name)
    )

    assert id(tree) == id(tree)
    assert tree.is_equal(tree)
    for edge in edges:
        assert tree.get_node((edge,)) is not None

    for m_name, path in sub_children:
        m = getattr(tree, m_name)
        assert m is not None
        assert m(path) is not None


def test_real_merge_with_table() -> None:
    tree_store = _get_tree_store()
    tree_inv = tree_store.load(host_name=HostName("tree_inv"))
    tree_status = tree_store.load(host_name=HostName("tree_status"))
    tree = tree_inv.merge_with(tree_status)
    assert "foobar" in tree.serialize()["Nodes"]
    table = tree.get_table(("foobar",))
    assert table is not None
    assert len(table.rows) == 5


@pytest.mark.parametrize(
    "paths, unavail",
    [
        (
            # container                   table                    attributes
            [
                (("hardware", "components"), None),
                (("networking", "interfaces"), None),
                (("software", "os"), None),
            ],
            [("hardware", "system"), ("software", "applications")],
        ),
    ],
)
def test_real_filtered_tree(
    paths: Sequence[tuple[tuple[str, ...], None]],
    unavail: Sequence[tuple[str, str]],
) -> None:
    tree = _get_tree_store().load(host_name=HostName("tree_new_interfaces"))
    filtered = tree.get_filtered_node(_make_filters(paths))
    assert id(tree) != id(filtered)
    assert not tree.is_equal(filtered)
    for path in unavail:
        assert filtered.get_node(path) is None


@pytest.mark.parametrize(
    "paths, amount_if_entries",
    [
        (
            [
                (("networking",), None),
            ],
            3178,
        ),
        (
            [
                (("networking",), []),
            ],
            None,
        ),
        (
            [
                (
                    ("networking",),
                    ["total_interfaces", "total_ethernet_ports", "available_ethernet_ports"],
                ),
            ],
            None,
        ),
        (
            [
                (("networking", "interfaces"), None),
            ],
            3178,
        ),
        (
            [
                (("networking", "interfaces"), []),
            ],
            3178,
        ),
        (
            [
                (("networking", "interfaces"), ["admin_status"]),
            ],
            326,
        ),
        (
            [
                (("networking", "interfaces"), ["admin_status", "FOOBAR"]),
            ],
            326,
        ),
        (
            [
                (("networking", "interfaces"), ["admin_status", "oper_status"]),
            ],
            652,
        ),
        (
            [
                (("networking", "interfaces"), ["admin_status", "oper_status", "FOOBAR"]),
            ],
            652,
        ),
    ],
)
def test_real_filtered_tree_networking(
    paths: Sequence[tuple[tuple[str, ...], Sequence[str]]],
    amount_if_entries: int,
) -> None:
    tree = _get_tree_store().load(host_name=HostName("tree_new_interfaces"))
    the_paths = list(paths)
    filtered = tree.get_filtered_node(_make_filters(paths))
    assert the_paths == paths
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

    old_tree = tree_store.load(host_name=tree_name_old)
    new_tree = tree_store.load(host_name=tree_name_new)
    delta_tree = old_tree.compare_with(new_tree)

    delta_raw_tree = delta_tree.serialize()
    assert isinstance(delta_raw_tree, dict)

    DeltaStructuredDataNode.deserialize(delta_raw_tree)


# Test filters


class ExpectedFilterResults(NamedTuple):
    nodes: bool
    restricted_nodes: bool
    attributes: bool
    restricted_attributes: bool
    columns: bool
    restricted_columns: bool


@pytest.mark.parametrize(
    "entry, expected_path, expected_filter_results",
    [
        # Tuple format
        (
            (("path", "to", "node"), None),
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=True,
                attributes=True,
                restricted_attributes=True,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            (("path", "to", "node"), []),
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=False,
                restricted_nodes=False,
                attributes=True,
                restricted_attributes=True,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            (("path", "to", "node"), ["key"]),
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=False,
                restricted_nodes=False,
                attributes=True,
                restricted_attributes=False,
                columns=True,
                restricted_columns=False,
            ),
        ),
        # Dict format
        (
            {
                "visible_raw_path": "path.to.node",
            },
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=True,
                attributes=True,
                restricted_attributes=True,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": ("choices", ["node"]),
            },
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=False,
                attributes=True,
                restricted_attributes=True,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": ("choices", ["key"]),
            },
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=True,
                attributes=True,
                restricted_attributes=False,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": ("choices", ["key"]),
            },
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=True,
                attributes=True,
                restricted_attributes=True,
                columns=True,
                restricted_columns=False,
            ),
        ),
        (
            {"visible_raw_path": "path.to.node", "nodes": "nothing"},
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=False,
                restricted_nodes=False,
                attributes=True,
                restricted_attributes=True,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": "nothing",
            },
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=True,
                attributes=False,
                restricted_attributes=False,
                columns=True,
                restricted_columns=True,
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": "nothing",
            },
            ("path", "to", "node"),
            ExpectedFilterResults(
                nodes=True,
                restricted_nodes=True,
                attributes=True,
                restricted_attributes=True,
                columns=False,
                restricted_columns=False,
            ),
        ),
    ],
)
def test_make_filter(  # type:ignore[no-untyped-def]
    entry, expected_path, expected_filter_results
) -> None:
    f = make_filter(entry)

    assert f.path == expected_path

    assert f.filter_nodes("node") is expected_filter_results.nodes
    assert f.filter_nodes("other") is expected_filter_results.restricted_nodes

    assert f.filter_attributes("key") is expected_filter_results.attributes
    assert f.filter_attributes("other") is expected_filter_results.restricted_attributes

    assert f.filter_columns("key") is expected_filter_results.columns
    assert f.filter_columns("other") is expected_filter_results.restricted_columns


# Test helper


@pytest.mark.parametrize(
    "raw_path, expected_path",
    [
        ("", tuple()),
        ("path.to.node_1", ("path", "to", "node_1")),
    ],
)
def test_parse_visible_tree_path(raw_path, expected_path) -> None:  # type:ignore[no-untyped-def]
    assert parse_visible_raw_path(raw_path) == expected_path


def test__is_table() -> None:
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

    tree = StructuredDataNode.deserialize(raw_tree)

    idx_node_attr = tree.get_node(("path-to", "idx-node", "0"))
    assert idx_node_attr is not None
    assert idx_node_attr.attributes.pairs == {"idx-attr": "value", "idx-enum": "v1, 1.0, 2"}
    assert idx_node_attr.table._rows == {}
    assert idx_node_attr.table.rows == []

    idx_sub_idx_node_attr = tree.get_node(
        ("path-to", "idx-node", "0", "idx-sub-idx-node", "0", "bar-node")
    )
    assert idx_sub_idx_node_attr is not None
    assert idx_sub_idx_node_attr.attributes.pairs == {"bar-attr": "value"}
    assert idx_sub_idx_node_attr.table._rows == {}
    assert idx_sub_idx_node_attr.table.rows == []

    idx_sub_node_attr = tree.get_node(("path-to", "idx-node", "0", "idx-sub-node", "foo-node"))
    assert idx_sub_node_attr is not None
    assert idx_sub_node_attr.attributes.pairs == {"foo-attr": "value"}
    assert idx_sub_node_attr.table._rows == {}
    assert idx_sub_node_attr.table.rows == []

    idx_table = tree.get_node(("path-to", "idx-node", "0", "idx-table"))
    assert idx_table is not None
    assert idx_table.attributes.pairs == {}
    assert idx_table.table._rows == {("value",): {"idx-col": "value"}}
    assert idx_table.table.rows == [{"idx-col": "value"}]

    attr_node = tree.get_node(("path-to", "node"))
    assert attr_node is not None
    assert attr_node.attributes.pairs == {"attr": "value"}
    assert attr_node.table._rows == {}
    assert attr_node.table.rows == []

    table_node = tree.get_node(("path-to", "table"))
    assert table_node is not None
    assert table_node.attributes.pairs == {}
    assert table_node.table._rows == {("value",): {"col": "value"}}
    assert table_node.table.rows == [{"col": "value"}]


def test_add_attributes() -> None:
    path = ("path-to", "node")
    retentions = {"key": RetentionIntervals(1, 2, 3)}

    node = StructuredDataNode(name="node", path=path)
    attributes = Attributes(retentions=retentions)
    node.add_attributes(attributes)

    assert node.attributes.path == path
    assert node.attributes.retentions == retentions


def test_add_table() -> None:
    path = ("path-to", "node")
    key_columns = ["key-0"]
    retentions: TableRetentions = {
        ("Value 0",): {"key-1": RetentionIntervals(1, 2, 3)},
    }

    node = StructuredDataNode(name="node", path=path)
    table = Table(
        key_columns=key_columns,
        retentions=retentions,
    )
    node.add_table(table)

    assert node.table.path == path
    assert node.table.key_columns == key_columns
    assert node.table.retentions == retentions


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
