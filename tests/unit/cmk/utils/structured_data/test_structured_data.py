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
    ImmutableDeltaTree,
    ImmutableTree,
    MutableTree,
    parse_visible_raw_path,
    RetentionIntervals,
    SDFilter,
    SDNodeName,
    SDPath,
    TreeStore,
)
from cmk.utils.type_defs import HostName


def _create_empty_mut_tree() -> MutableTree:
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes
    root = MutableTree()
    root.add_rows(path=["path-to-nta", "nt"], key_columns=[], rows=[])
    root.add_pairs(path=["path-to-nta", "na"], pairs={})
    root.add_pairs(path=["path-to-nta", "ta"], pairs={})
    root.add_rows(path=["path-to-nta", "ta"], key_columns=[], rows=[])
    return root


def _create_empty_imm_tree() -> ImmutableTree:
    return ImmutableTree(_create_empty_mut_tree().tree)


def _create_filled_mut_tree() -> MutableTree:
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes
    root = MutableTree()
    root.add_rows(
        path=["path-to-nta", "nt"],
        key_columns=["nt0"],
        rows=[
            {"nt0": "NT 00", "nt1": "NT 01"},
            {"nt0": "NT 10", "nt1": "NT 11"},
        ],
    )
    root.add_pairs(path=["path-to-nta", "na"], pairs={"na0": "NA 0", "na1": "NA 1"})
    root.add_pairs(path=["path-to-nta", "ta"], pairs={"ta0": "TA 0", "ta1": "TA 1"})
    root.add_rows(
        path=["path-to-nta", "ta"],
        key_columns=["ta0"],
        rows=[
            {"ta0": "TA 00", "ta1": "TA 01"},
            {"ta0": "TA 10", "ta1": "TA 11"},
        ],
    )
    return root


def _create_filled_imm_tree() -> ImmutableTree:
    return ImmutableTree(_create_filled_mut_tree().tree)


def test_serialize_empty_mut_tree() -> None:
    assert _create_empty_mut_tree().serialize() == {"Attributes": {}, "Table": {}, "Nodes": {}}


def test_serialize_filled_mut_tree() -> None:
    raw_tree = _create_filled_mut_tree().serialize()
    assert raw_tree["Attributes"] == {}
    assert raw_tree["Table"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Attributes"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Table"] == {}

    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["na"]["Attributes"]["Pairs"] == {
        "na0": "NA 0",
        "na1": "NA 1",
    }
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["na"]["Table"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["na"]["Nodes"] == {}

    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Attributes"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Table"]["KeyColumns"] == ["nt0"]
    nt_rows = raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Table"]["Rows"]
    assert len(nt_rows) == 2
    for row in [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]:
        assert row in nt_rows
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Nodes"] == {}

    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Attributes"]["Pairs"] == {
        "ta0": "TA 0",
        "ta1": "TA 1",
    }
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Table"]["KeyColumns"] == ["ta0"]
    ta_rows = raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Table"]["Rows"]
    assert len(ta_rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in ta_rows
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Nodes"] == {}


def test_deserialize_empty_imm_tree() -> None:
    assert ImmutableTree.deserialize({}) == MutableTree()
    assert ImmutableTree.deserialize({}) == ImmutableTree()


def test_deserialize_filled_imm_tree() -> None:
    tree = ImmutableTree.deserialize(
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
    assert _create_empty_imm_tree().difference(_create_empty_imm_tree()).serialize() == {
        "Attributes": {},
        "Table": {},
        "Nodes": {},
    }


def test_serialize_filled_delta_tree() -> None:
    raw_tree = _create_empty_imm_tree().difference(_create_filled_imm_tree()).serialize()
    assert raw_tree["Attributes"] == {}
    assert raw_tree["Table"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Attributes"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Table"] == {}

    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["na"]["Attributes"]["Pairs"] == {
        "na0": ("NA 0", None),
        "na1": ("NA 1", None),
    }
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["na"]["Table"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["na"]["Nodes"] == {}

    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Attributes"] == {}
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Table"]["KeyColumns"] == ["nt0"]
    nt_rows = raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Table"]["Rows"]
    assert len(nt_rows) == 2
    for row in [
        {"nt0": ("NT 00", None), "nt1": ("NT 01", None)},
        {"nt0": ("NT 10", None), "nt1": ("NT 11", None)},
    ]:
        assert row in nt_rows
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["nt"]["Nodes"] == {}

    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Attributes"]["Pairs"] == {
        "ta0": ("TA 0", None),
        "ta1": ("TA 1", None),
    }
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Table"]["KeyColumns"] == ["ta0"]
    ta_rows = raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Table"]["Rows"]
    assert len(ta_rows) == 2
    for row in [
        {"ta0": ("TA 00", None), "ta1": ("TA 01", None)},
        {"ta0": ("TA 10", None), "ta1": ("TA 11", None)},
    ]:
        assert row in ta_rows
    assert raw_tree["Nodes"]["path-to-nta"]["Nodes"]["ta"]["Nodes"] == {}


def test_deserialize_empty_delta_tree() -> None:
    assert not ImmutableDeltaTree.deserialize(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {},
        }
    )


def test_deserialize_filled_delta_tree() -> None:
    delta_tree = ImmutableDeltaTree.deserialize(
        {
            "Attributes": {},
            "Nodes": {
                "path-to-nta": {
                    "Attributes": {},
                    "Nodes": {
                        "na": {
                            "Attributes": {"Pairs": {"na0": ("NA 0", None), "na1": ("NA 1", None)}},
                            "Nodes": {},
                            "Table": {},
                        },
                        "nt": {
                            "Attributes": {},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["nt0"],
                                "Rows": [
                                    {"nt0": ("NT 00", None), "nt1": ("NT 01", None)},
                                    {"nt0": ("NT 10", None), "nt1": ("NT 11", None)},
                                ],
                            },
                        },
                        "ta": {
                            "Attributes": {"Pairs": {"ta0": ("TA 0", None), "ta1": ("TA 1", None)}},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["ta0"],
                                "Rows": [
                                    {"ta0": ("TA 00", None), "ta1": ("TA 01", None)},
                                    {"ta0": ("TA 10", None), "ta1": ("TA 11", None)},
                                ],
                            },
                        },
                    },
                    "Table": {},
                }
            },
            "Table": {},
        }
    )
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 12


def test_get_tree_empty() -> None:
    root = _create_empty_imm_tree()
    nta = root.get_tree(("path-to-nta",))
    nt = root.get_tree(("path-to-nta", "nt"))
    na = root.get_tree(("path-to-nta", "na"))
    ta = root.get_tree(("path-to-nta", "ta"))
    assert not bool(nta)
    assert nta.tree.path == ("path-to-nta",)
    assert not bool(nt)
    assert nt.tree.path == ("path-to-nta", "nt")
    assert not bool(na)
    assert na.tree.path == ("path-to-nta", "na")
    assert not bool(ta)
    assert ta.tree.path == ("path-to-nta", "ta")
    assert not bool(root.get_tree(("path-to", "unknown")))
    assert root.tree.count_entries() == 0


def test_get_tree_not_empty() -> None:
    root = _create_filled_imm_tree()
    nta = root.get_tree(("path-to-nta",))
    nt = root.get_tree(("path-to-nta", "nt"))
    na = root.get_tree(("path-to-nta", "na"))
    ta = root.get_tree(("path-to-nta", "ta"))
    assert bool(nta)
    assert nta.tree.path == ("path-to-nta",)

    assert bool(nt)
    assert nt.tree.path == ("path-to-nta", "nt")
    assert root.get_attribute(("path-to-nta", "nt"), "foo") is None
    nt_rows = root.get_rows(("path-to-nta", "nt"))
    assert len(nt_rows) == 2
    for row in [
        {"nt0": "NT 00", "nt1": "NT 01"},
        {"nt0": "NT 10", "nt1": "NT 11"},
    ]:
        assert row in nt_rows

    assert bool(na)
    assert na.tree.path == ("path-to-nta", "na")
    assert root.get_attribute(("path-to-nta", "na"), "na0") == "NA 0"
    assert root.get_attribute(("path-to-nta", "na"), "na1") == "NA 1"
    assert root.get_attribute(("path-to-nta", "na"), "foo") is None
    assert root.get_rows(("path-to-nta", "na")) == []

    assert bool(ta)
    assert ta.tree.path == ("path-to-nta", "ta")
    assert root.get_attribute(("path-to-nta", "ta"), "ta0") == "TA 0"
    assert root.get_attribute(("path-to-nta", "ta"), "ta1") == "TA 1"
    assert root.get_attribute(("path-to-nta", "ta"), "foo") is None
    ta_rows = root.get_rows(("path-to-nta", "ta"))
    assert len(ta_rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in ta_rows

    assert not bool(root.get_tree(("path-to", "unknown")))
    assert root.tree.count_entries() == 12


def test_add_pairs_or_rows() -> None:
    root = _create_filled_mut_tree()
    root.add_pairs(path=["path-to-nta", "node"], pairs={"sn0": "SN 0", "sn1": "SN 1"})
    root.add_rows(
        path=["path-to-nta", "node"],
        key_columns=["sn0"],
        rows=[
            {"sn0": "SN 00", "sn1": "SN 01"},
            {"sn0": "SN 10", "sn1": "SN 11"},
        ],
    )
    assert root.count_entries() == 18


def test_compare_tree_with_itself_1() -> None:
    empty_root = _create_empty_imm_tree()
    delta_tree = empty_root.difference(empty_root)
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_compare_tree_with_itself_2() -> None:
    filled_root = _create_filled_imm_tree()
    delta_tree = filled_root.difference(filled_root)
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_compare_tree_1() -> None:
    delta_tree = _create_empty_imm_tree().difference(_create_filled_imm_tree())
    stats = delta_tree.get_stats()
    assert stats["new"] == 0
    assert stats["changed"] == 0
    assert stats["removed"] == 12


def test_compare_tree_2() -> None:
    delta_tree = _create_filled_imm_tree().difference(_create_empty_imm_tree())
    stats = delta_tree.get_stats()
    assert stats["new"] == 12
    assert stats["changed"] == 0
    assert stats["removed"] == 0


def test_filter_delta_tree_nt() -> None:
    filtered = (
        _create_filled_imm_tree()
        .difference(_create_empty_imm_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to-nta", "nt"),
                    filter_pairs=lambda k: k in ["nt1"],
                    filter_columns=lambda k: k in ["nt1"],
                    filter_nodes=lambda n: False,
                )
            ],
        )
    )

    assert not filtered.get_tree(("path-to-nta", "na"))
    assert not filtered.get_tree(("path-to-nta", "ta"))

    filtered_child = filtered.get_tree(("path-to-nta", "nt"))
    assert bool(filtered_child)
    assert filtered_child.tree.path == ("path-to-nta", "nt")
    assert filtered_child.tree.attributes.pairs == {}
    assert len(filtered_child.tree.table.rows) == 2
    for row in (
        {"nt1": (None, "NT 01")},
        {"nt1": (None, "NT 11")},
    ):
        assert row in filtered_child.tree.table.rows


def test_filter_delta_tree_na() -> None:
    filtered = (
        _create_filled_imm_tree()
        .difference(_create_empty_imm_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to-nta", "na"),
                    filter_pairs=lambda k: k in ["na1"],
                    filter_columns=lambda k: k in ["na1"],
                    filter_nodes=lambda n: False,
                )
            ],
        )
    )

    assert not filtered.get_tree(("path-to-nta", "nt"))
    assert not filtered.get_tree(("path-to-nta", "ta"))

    filtered_child = filtered.get_tree(("path-to-nta", "na"))
    assert bool(filtered_child)
    assert filtered_child.tree.path == ("path-to-nta", "na")
    assert filtered_child.tree.attributes.pairs == {"na1": (None, "NA 1")}
    assert filtered_child.tree.table.rows == []


def test_filter_delta_tree_ta() -> None:
    filtered = (
        _create_filled_imm_tree()
        .difference(_create_empty_imm_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to-nta", "ta"),
                    filter_pairs=lambda k: k in ["ta1"],
                    filter_columns=lambda k: k in ["ta1"],
                    filter_nodes=lambda n: False,
                )
            ],
        )
    )

    assert not filtered.get_tree(("path-to-nta", "nt"))
    assert not filtered.get_tree(("path-to-nta", "na"))

    filtered_child = filtered.get_tree(("path-to-nta", "ta"))
    assert bool(filtered_child)
    assert filtered_child.tree.path == ("path-to-nta", "ta")
    assert filtered_child.tree.attributes.pairs == {"ta1": (None, "TA 1")}
    assert len(filtered_child.tree.table.rows) == 2
    for row in (
        {"ta1": (None, "TA 01")},
        {"ta1": (None, "TA 11")},
    ):
        assert row in filtered_child.tree.table.rows


def test_filter_delta_tree_nta_ta() -> None:
    filtered = (
        _create_filled_imm_tree()
        .difference(_create_empty_imm_tree())
        .filter(
            [
                SDFilter(
                    path=("path-to-nta", "ta"),
                    filter_pairs=lambda k: k in ["ta0"],
                    filter_columns=lambda k: k in ["ta0"],
                    filter_nodes=lambda n: False,
                ),
                SDFilter(
                    path=("path-to-nta", "ta"),
                    filter_pairs=lambda k: False,
                    filter_columns=lambda k: k in ["ta1"],
                    filter_nodes=lambda n: False,
                ),
            ],
        )
    )

    nta = filtered.get_tree(("path-to-nta",))
    assert bool(nta)
    assert nta.tree.attributes.pairs == {}
    assert nta.tree.table.rows == []

    assert not filtered.get_tree(("path-to-nta", "nt"))
    assert not filtered.get_tree(("path-to-nta", "na"))

    filtered_ta = filtered.get_tree(("path-to-nta", "ta"))
    assert bool(filtered_ta)
    assert filtered_ta.tree.attributes.pairs == {"ta0": (None, "TA 0")}
    assert len(filtered_ta.tree.table.rows) == 2
    for row in (
        {"ta0": (None, "TA 00"), "ta1": (None, "TA 01")},
        {"ta0": (None, "TA 10"), "ta1": (None, "TA 11")},
    ):
        assert row in filtered_ta.tree.table.rows


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
    previous_pairs: Mapping[str, str],
    current_pairs: Mapping[str, str],
    result: tuple[int, int, int],
) -> None:
    previous_tree = MutableTree()
    previous_tree.add_pairs(path=[], pairs=previous_pairs)

    current_tree = MutableTree()
    current_tree.add_pairs(path=[], pairs=current_pairs)

    stats = (
        ImmutableTree(current_tree.tree).difference(ImmutableTree(previous_tree.tree)).get_stats()
    )
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
    previous_rows: Sequence[Mapping[str, str | int]],
    current_rows: Sequence[Mapping[str, str | int]],
    result: tuple[int, int, int],
) -> None:
    previous_tree = MutableTree()
    previous_tree.add_rows(path=[], key_columns=["id"], rows=previous_rows)

    current_tree = MutableTree()
    current_tree.add_rows(path=[], key_columns=["id"], rows=current_rows)

    delta_tree = ImmutableTree(current_tree.tree).difference(ImmutableTree(previous_tree.tree))
    if any(result):
        assert delta_tree
    else:
        assert not delta_tree

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
    previous_row: dict[str, str],
    current_row: dict[str, str],
    expected_keys: set[str],
) -> None:
    previous_tree = MutableTree()
    previous_tree.add_rows(path=[], key_columns=["id"], rows=[previous_row])

    current_tree = MutableTree()
    current_tree.add_rows(path=[], key_columns=["id"], rows=[current_row])

    delta_tree = ImmutableTree(current_tree.tree).difference(ImmutableTree(previous_tree.tree))
    assert {k for r in delta_tree.tree.table.rows for k in r} == expected_keys


def test_filter_tree_no_paths() -> None:
    assert not _create_filled_imm_tree().filter([])


def test_filter_tree_wrong_node() -> None:
    filled_root = _create_filled_imm_tree()
    filters = [
        SDFilter(
            path=("path-to-nta", "ta"),
            filter_pairs=lambda k: True,
            filter_columns=lambda k: True,
            filter_nodes=lambda k: True,
        ),
    ]
    filtered = filled_root.filter(filters)
    assert not filtered.get_tree(("path-to-nta", "na"))
    assert not filtered.get_tree(("path-to-nta", "nt"))
    assert bool(filtered.get_tree(("path-to-nta", "ta")))


def test_filter_tree_paths_no_keys() -> None:
    filled_root = _create_filled_imm_tree()
    filters = [
        SDFilter(
            path=("path-to-nta", "ta"),
            filter_pairs=lambda k: True,
            filter_columns=lambda k: True,
            filter_nodes=lambda k: True,
        ),
    ]
    filtered_root = filled_root.filter(filters)

    assert filtered_root.get_attribute(("path-to-nta", "ta"), "ta0") == "TA 0"
    assert filtered_root.get_attribute(("path-to-nta", "ta"), "ta1") == "TA 1"
    assert filtered_root.get_attribute(("path-to-nta", "ta"), "foo") is None

    rows = filtered_root.get_rows(("path-to-nta", "ta"))
    assert len(rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in rows


def test_filter_tree_paths_and_keys() -> None:
    filled_root = _create_filled_imm_tree()
    filters = [
        SDFilter(
            path=("path-to-nta", "ta"),
            filter_pairs=lambda k: k in ["ta1"],
            filter_columns=lambda k: k in ["ta1"],
            filter_nodes=lambda k: True,
        ),
    ]
    filtered_root = filled_root.filter(filters)

    assert filtered_root.get_attribute(("path-to-nta", "ta"), "ta1") == "TA 1"
    assert filtered_root.get_attribute(("path-to-nta", "ta"), "foo") is None

    rows = filtered_root.get_rows(("path-to-nta", "ta"))
    assert len(rows) == 2
    for row in [
        {"ta1": "TA 01"},
        {"ta1": "TA 11"},
    ]:
        assert row in rows


def test_filter_tree_mixed() -> None:
    filled_root = _create_filled_mut_tree()
    filled_root.add_pairs(
        path=["path-to", "another", "node1"],
        pairs={"ak11": "Another value 11", "ak12": "Another value 12"},
    )
    filled_root.add_rows(
        path=["path-to", "another", "node2"],
        key_columns=["ak21"],
        rows=[
            {
                "ak21": "Another value 211",
                "ak22": "Another value 212",
            },
            {
                "ak21": "Another value 221",
                "ak22": "Another value 222",
            },
        ],
    )

    filters = [
        SDFilter(
            path=("path-to", "another"),
            filter_pairs=lambda k: True,
            filter_columns=lambda k: True,
            filter_nodes=lambda k: True,
        ),
        SDFilter(
            path=("path-to-nta", "ta"),
            filter_pairs=lambda k: k in ["ta0"],
            filter_columns=lambda k: k in ["ta0"],
            filter_nodes=lambda k: True,
        ),
    ]
    filtered_root = ImmutableTree(filled_root.tree).filter(filters)

    assert filtered_root.tree.count_entries() == 9
    assert not filtered_root.get_tree(("path-to-nta", "nt"))
    assert not filtered_root.get_tree(("path-to-nta", "na"))
    assert bool(filtered_root.get_tree(("path-to", "another", "node1")))
    assert bool(filtered_root.get_tree(("path-to", "another", "node2")))


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


def test_save_tree(tmp_path: Path) -> None:
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
def test_load_real_tree(tree_name: HostName) -> None:
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
def test_real_tree_is_equal(tree_name_x: HostName, tree_name_y: HostName) -> None:
    tree_store = _get_tree_store()
    tree_x = tree_store.load(host_name=tree_name_x)
    tree_y = tree_store.load(host_name=tree_name_y)

    if tree_name_x == tree_name_y:
        assert tree_x == tree_y
    else:
        assert tree_x != tree_y


def test_real_tree_order() -> None:
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
def test_save_and_load_real_tree(tree_name: HostName, tmp_path: Path) -> None:
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
def test_count_entries(tree_name: HostName, result: int) -> None:
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
def test_compare_real_tree_with_itself(tree_name: HostName) -> None:
    tree = _get_tree_store().load(host_name=tree_name)
    stats = tree.difference(tree).get_stats()
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
    tree_store = _get_tree_store()
    old_tree = tree_store.load(host_name=tree_name_old)
    new_tree = tree_store.load(host_name=tree_name_new)
    stats = new_tree.difference(old_tree).get_stats()
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
    tree = _get_tree_store().load(host_name=tree_name)
    for edge_t in edges_t:
        assert tree.tree.get_node((edge_t,)) is not None
    for edge_f in edges_f:
        assert tree.tree.get_node((edge_f,)) is None


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
    tree = _get_tree_store().load(host_name=tree_name)
    assert len(list(tree.tree.nodes)) == amount_of_nodes


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
                    filter_pairs=lambda k: True,
                    filter_columns=lambda k: True,
                    filter_nodes=lambda k: True,
                ),
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_pairs=lambda k: True,
                    filter_columns=lambda k: True,
                    filter_nodes=lambda k: True,
                ),
                SDFilter(
                    path=("software", "os"),
                    filter_pairs=lambda k: True,
                    filter_columns=lambda k: True,
                    filter_nodes=lambda k: True,
                ),
            ],
            [("hardware", "system"), ("software", "applications")],
        ),
    ],
)
def test_filter_real_tree(
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
                    filter_pairs=lambda k: True,
                    filter_columns=lambda k: True,
                    filter_nodes=lambda k: True,
                )
            ],
            3178,
        ),
        (
            [
                SDFilter(
                    path=("networking",),
                    filter_pairs=(
                        lambda k: k
                        in ["total_interfaces", "total_ethernet_ports", "available_ethernet_ports"]
                    ),
                    filter_columns=(
                        lambda k: k
                        in ["total_interfaces", "total_ethernet_ports", "available_ethernet_ports"]
                    ),
                    filter_nodes=lambda k: False,
                ),
            ],
            None,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_pairs=lambda k: True,
                    filter_columns=lambda k: True,
                    filter_nodes=lambda k: True,
                ),
            ],
            3178,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_pairs=lambda k: k in ["admin_status"],
                    filter_columns=lambda k: k in ["admin_status"],
                    filter_nodes=lambda k: False,
                ),
            ],
            326,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_pairs=lambda k: k in ["admin_status", "FOOBAR"],
                    filter_columns=lambda k: k in ["admin_status", "FOOBAR"],
                    filter_nodes=lambda k: False,
                ),
            ],
            326,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_pairs=lambda k: k in ["admin_status", "oper_status"],
                    filter_columns=lambda k: k in ["admin_status", "oper_status"],
                    filter_nodes=lambda k: False,
                ),
            ],
            652,
        ),
        (
            [
                SDFilter(
                    path=("networking", "interfaces"),
                    filter_pairs=lambda k: k in ["admin_status", "oper_status", "FOOBAR"],
                    filter_columns=lambda k: k in ["admin_status", "oper_status", "FOOBAR"],
                    filter_nodes=lambda k: False,
                ),
            ],
            652,
        ),
    ],
)
def test_filter_networking_tree(
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


def test_filter_networking_tree_empty() -> None:
    tree = _get_tree_store().load(host_name=HostName("tree_new_interfaces"))
    filtered = tree.filter(
        [
            SDFilter(
                path=("networking",),
                filter_pairs=lambda k: False,
                filter_columns=lambda k: False,
                filter_nodes=lambda k: False,
            ),
        ]
    ).tree
    assert filtered.get_node(("networking",)) is None
    assert filtered.get_node(("hardware",)) is None
    assert filtered.get_node(("software",)) is None


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

    tree = ImmutableTree.deserialize(raw_tree).tree

    idx_node_attr = tree.get_node(("path-to", "idx-node", "0"))
    assert idx_node_attr is not None
    assert idx_node_attr.attributes.pairs == {"idx-attr": "value", "idx-enum": "v1, 1.0, 2"}
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


def test_update_from_previous_1() -> None:
    previous_tree = ImmutableTree.deserialize(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [
                    {"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"},
                ],
                "Retentions": {
                    ("KC",): {
                        "c1": (1, 2, 3),
                        "c2": (1, 2, 3),
                    }
                },
            },
            "Nodes": {},
        }
    )
    current_tree = MutableTree()
    current_tree.add_rows(
        path=[],
        key_columns=["kc"],
        rows=[
            {"kc": "KC", "c1": "C1: cur", "c3": "C3: only cur"},
        ],
    )
    current_tree.update_rows(
        0,  # now
        (),  # path
        previous_tree,
        lambda k: True,  # filter func
        RetentionIntervals(4, 5, 6),
    )

    assert current_tree.tree.table.key_columns == ["kc"]
    assert current_tree.tree.table.retentions == {
        ("KC",): {
            "c1": RetentionIntervals(4, 5, 6),
            "c2": RetentionIntervals(1, 2, 3),
            "c3": RetentionIntervals(4, 5, 6),
            "kc": RetentionIntervals(4, 5, 6),
        }
    }
    assert ImmutableTree(current_tree.tree).get_rows(()) == [
        {"c1": "C1: cur", "c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}
    ]


def test_update_from_previous_2() -> None:
    previous_tree = ImmutableTree.deserialize(
        {
            "Attributes": {},
            "Table": {
                "KeyColumns": ["kc"],
                "Rows": [
                    {"kc": "KC", "c1": "C1: prev C1", "c2": "C2: only prev"},
                ],
                "Retentions": {
                    ("KC",): {
                        "c1": (1, 2, 3),
                        "c2": (1, 2, 3),
                    }
                },
            },
            "Nodes": {},
        }
    )
    current_tree = MutableTree()
    current_tree.add_rows(
        path=[],
        key_columns=["kc"],
        rows=[
            {"kc": "KC", "c3": "C3: only cur"},
        ],
    )
    current_tree.update_rows(
        0,  # now
        (),  # path
        previous_tree,
        lambda k: k in ["c2", "c3"],  # filter func
        RetentionIntervals(4, 5, 6),
    )
    assert current_tree.tree.table.key_columns == ["kc"]
    assert current_tree.tree.table.retentions == {
        ("KC",): {
            "c2": RetentionIntervals(1, 2, 3),
            "c3": RetentionIntervals(4, 5, 6),
        }
    }
    assert ImmutableTree(current_tree.tree).get_rows(()) == [
        {"c2": "C2: only prev", "c3": "C3: only cur", "kc": "KC"}
    ]
