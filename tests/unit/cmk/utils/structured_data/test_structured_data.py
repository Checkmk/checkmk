#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import shutil
from pathlib import Path
from typing import Dict, List, NamedTuple

import pytest

from testlib import cmk_path

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.structured_data import (
    Attributes,
    make_filter,
    parse_visible_raw_path,
    StructuredDataNode,
    StructuredDataStore,
    Table,
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

    root.setdefault_node(["path", "to", "nta", "nt"])
    root.setdefault_node(["path", "to", "nta", "na"])
    root.setdefault_node(["path", "to", "nta", "ta"])

    return root


def _create_filled_tree():
    # Abbreviations:
    # nta: has StructuredDataNode, Table, Attributes
    # nt: has StructuredDataNode, Table
    # na: has StructuredDataNode, Attributes
    # ta: has Table, Attributes

    root = StructuredDataNode()

    nt = root.setdefault_node(["path", "to", "nta", "nt"])
    na = root.setdefault_node(["path", "to", "nta", "na"])
    ta = root.setdefault_node(["path", "to", "nta", "ta"])

    nt.table.add_rows([
        {
            "nt0": "NT 00",
            "nt1": "NT 01"
        },
        {
            "nt0": "NT 10",
            "nt1": "NT 11"
        },
    ])

    na.attributes.add_pairs({"na0": "NA 0", "na1": "NA 1"})

    ta.table.add_rows([
        {
            "ta0": "TA 00",
            "ta1": "TA 01"
        },
        {
            "ta0": "TA 10",
            "ta1": "TA 11"
        },
    ])
    ta.attributes.add_pairs({"ta0": "TA 0", "ta1": "TA 1"})

    return root


def test_get_node():
    root = _create_empty_tree()

    nta = root.get_node(["path", "to", "nta"])
    nt = root.get_node(["path", "to", "nta", "nt"])
    na = root.get_node(["path", "to", "nta", "na"])
    ta = root.get_node(["path", "to", "nta", "ta"])

    assert nta is not None
    assert nt is not None
    assert na is not None
    assert ta is not None

    assert root.get_node(["path", "to", "unknown"]) is None


def test_set_path():
    root = _create_empty_tree()

    nta = root.get_node(["path", "to", "nta"])
    nt = root.get_node(["path", "to", "nta", "nt"])
    na = root.get_node(["path", "to", "nta", "na"])
    ta = root.get_node(["path", "to", "nta", "ta"])

    assert nta.attributes.path == tuple(["path", "to", "nta"])
    assert nta.table.path == tuple(["path", "to", "nta"])
    assert nta.path == tuple(["path", "to", "nta"])

    assert nt.attributes.path == tuple(["path", "to", "nta", "nt"])
    assert nt.table.path == tuple(["path", "to", "nta", "nt"])
    assert nt.path == tuple(["path", "to", "nta", "nt"])

    assert na.attributes.path == tuple(["path", "to", "nta", "na"])
    assert na.table.path == tuple(["path", "to", "nta", "na"])
    assert na.path == tuple(["path", "to", "nta", "na"])

    assert ta.attributes.path == tuple(["path", "to", "nta", "ta"])
    assert ta.table.path == tuple(["path", "to", "nta", "ta"])
    assert ta.path == tuple(["path", "to", "nta", "ta"])


def test_empty_but_different_structure():
    root = _create_empty_tree()

    nt = root.get_node(["path", "to", "nta", "nt"])
    na = root.get_node(["path", "to", "nta", "na"])
    ta = root.get_node(["path", "to", "nta", "ta"])

    assert nt.attributes.pairs == {}
    assert nt.attributes.is_empty()
    assert nt.table.rows == []
    assert nt.table.is_empty()

    assert na.attributes.pairs == {}
    assert na.attributes.is_empty()
    assert na.table.rows == []
    assert na.table.is_empty()

    assert ta.attributes.pairs == {}
    assert ta.attributes.is_empty()
    assert ta.table.rows == []
    assert ta.table.is_empty()

    assert root.is_empty()
    assert root.count_entries() == 0
    assert not root.is_equal(StructuredDataNode())


def test_not_empty():
    root = _create_filled_tree()

    nt = root.get_node(["path", "to", "nta", "nt"])
    na = root.get_node(["path", "to", "nta", "na"])
    ta = root.get_node(["path", "to", "nta", "ta"])

    assert nt.attributes.pairs == {}
    assert nt.attributes.is_empty()
    assert nt.table.rows == [
        {
            "nt0": "NT 00",
            "nt1": "NT 01"
        },
        {
            "nt0": "NT 10",
            "nt1": "NT 11"
        },
    ]
    assert not nt.table.is_empty()

    assert na.attributes.pairs == {"na0": "NA 0", "na1": "NA 1"}
    assert not na.attributes.is_empty()
    assert na.table.rows == []
    assert na.table.is_empty()

    assert ta.attributes.pairs == {"ta0": "TA 0", "ta1": "TA 1"}
    assert not ta.attributes.is_empty()
    assert ta.table.rows == [
        {
            "ta0": "TA 00",
            "ta1": "TA 01"
        },
        {
            "ta0": "TA 10",
            "ta1": "TA 11"
        },
    ]
    assert not ta.table.is_empty()

    assert not root.is_empty()
    assert root.count_entries() == 12


def test_add_node():
    root = _create_filled_tree()

    sub_node = StructuredDataNode()
    sub_node.attributes.add_pairs({"sn0": "SN 0", "sn1": "SN 1"})
    sub_node.table.add_rows([
        {
            "sn0": "SN 00",
            "sn1": "SN 01"
        },
        {
            "sn0": "SN 10",
            "sn1": "SN 11"
        },
    ])

    node = root.get_node(["path", "to", "nta"]).add_node("node", sub_node)

    # Do not modify orig node.
    assert sub_node.attributes.path == tuple()
    assert sub_node.table.path == tuple()
    assert sub_node.path == tuple()

    assert node.attributes.path == tuple(["path", "to", "nta", "node"])
    assert node.table.path == tuple(["path", "to", "nta", "node"])
    assert node.path == tuple(["path", "to", "nta", "node"])

    assert not root.is_empty()
    assert root.count_entries() == 18


def test_compare_with_self():
    empty_root = _create_empty_tree()
    delta_result0 = empty_root.compare_with(empty_root)
    assert delta_result0.counter['new'] == 0
    assert delta_result0.counter['changed'] == 0
    assert delta_result0.counter['removed'] == 0
    assert delta_result0.delta.is_empty()

    filled_root = _create_filled_tree()
    delta_result1 = filled_root.compare_with(filled_root)
    assert delta_result1.counter['new'] == 0
    assert delta_result1.counter['changed'] == 0
    assert delta_result1.counter['removed'] == 0
    assert delta_result1.delta.is_empty()


def test_compare_with():
    # Results must be symmetric
    empty_root = _create_empty_tree()
    filled_root = _create_filled_tree()

    delta_result0 = empty_root.compare_with(filled_root)
    assert delta_result0.counter['new'] == 0
    assert delta_result0.counter['changed'] == 0
    assert delta_result0.counter['removed'] == 12

    delta_result1 = filled_root.compare_with(empty_root)
    assert delta_result1.counter['new'] == 12
    assert delta_result1.counter['changed'] == 0
    assert delta_result1.counter['removed'] == 0


@pytest.mark.parametrize("old_attributes_data, new_attributes_data, result", [
    ({}, {}, (0, 0, 0)),
    ({
        "k0": "v0"
    }, {
        "k0": "v0"
    }, (0, 0, 0)),
    ({
        "k0": "v0"
    }, {}, (0, 0, 1)),
    ({}, {
        "k0": "v0"
    }, (1, 0, 0)),
    ({
        "k0": "v00"
    }, {
        "k0": "v01"
    }, (0, 1, 0)),
    ({
        "k0": "v0",
        "k1": "v1",
    }, {
        "k1": "v1"
    }, (0, 0, 1)),
    ({
        "k1": "v1"
    }, {
        "k0": "v0",
        "k1": "v1",
    }, (1, 0, 0)),
    ({
        "k0": "v00",
        "k1": "v1",
    }, {
        "k0": "v01",
        "k1": "v1",
    }, (0, 1, 0)),
])
def test_attributes_compare_with(old_attributes_data, new_attributes_data, result):
    old_attributes = Attributes()
    old_attributes.add_pairs(old_attributes_data)

    new_attributes = Attributes()
    new_attributes.add_pairs(new_attributes_data)

    delta_result = new_attributes.compare_with(old_attributes)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == result


@pytest.mark.parametrize("old_table_data, new_table_data, result", [
    ([], [], (0, 0, 0)),
    ([{
        "id": "1",
        "val": 0
    }], [], (0, 0, 2)),
    ([], [{
        "id": "1",
        "val": 0
    }], (2, 0, 0)),
    ([{
        "id": "1",
        "val": 0
    }], [{
        "id": "1",
        "val": 0
    }], (0, 0, 0)),
    ([{
        "id": "1",
        "val": 0
    }, {
        "id": "2",
        "val": 1
    }], [{
        "id": "1",
        "val": 0
    }], (0, 0, 2)),
    ([{
        "id": "1",
        "val": 0
    }], [{
        "id": "1",
        "val": 0
    }, {
        "id": "2",
        "val": 1
    }], (2, 0, 0)),
    ([{
        "id": "1",
        "val1": 1
    }], [{
        "id": "1",
        "val1": 1,
        "val2": 1
    }], (1, 0, 0)),
    ([{
        "id": "1",
        "val": 0
    }], [{
        "id": "1",
        "val": 1
    }], (0, 1, 0)),
    ([{
        "id": "1",
        "val1": 1,
        "val2": -1
    }], [{
        "id": "1",
        "val1": 1
    }], (0, 0, 1)),
    ([{
        "id": "1",
        "val1": 0
    }, {
        "id": "2",
        "val1": 0,
        "val2": 0
    }, {
        "id": "3",
        "val1": 0
    }], [{
        "id": "1",
        "val1": 1
    }, {
        "id": "2",
        "val1": 0
    }, {
        "id": "3",
        "val1": 0,
        "val2": 1
    }], (1, 1, 1)),
    ([{
        "id": "1",
        "val1": 1
    }, {
        "id": "2",
        "val1": 1
    }], [{
        "id": "1",
        "val1": 1,
        "val2": -1
    }, {
        "id": "2",
        "val1": 1,
        "val2": -1
    }], (2, 0, 0)),
    ([{
        "id": "1",
        "val": 1
    }, {
        "id": "2",
        "val": 3
    }], [{
        "id": "1",
        "val": 2
    }, {
        "id": "2",
        "val": 4
    }], (0, 2, 0)),
    ([{
        "id": "1",
        "val1": 1,
        "val2": -1
    }, {
        "id": "2",
        "val1": 1,
        "val2": -1
    }], [{
        "id": "1",
        "val1": 1
    }, {
        "id": "2",
        "val1": 1
    }], (0, 0, 2)),
    ([{
        "id": "2",
        "val": 1
    }, {
        "id": "3",
        "val": 3
    }, {
        "id": "1",
        "val": 0
    }], [{
        "id": "2",
        "val": 2
    }, {
        "id": "1",
        "val": 0
    }, {
        "id": "3",
        "val": 4
    }], (0, 2, 0)),
    ([{
        "id": "1",
        "val": 1
    }, {
        "id": "2",
        "val": 3
    }, {
        "id": "3",
        "val": 0
    }], [{
        "id": "0",
        "val": 2
    }, {
        "id": "1",
        "val": 0
    }, {
        "id": "2",
        "val": 4
    }, {
        "id": "3",
        "val": 1
    }], (8, 0, 6)),
])
def test_table_compare_with(old_table_data, new_table_data, result):
    old_table = Table()
    old_table.add_rows(old_table_data)
    new_table = Table()
    new_table.add_rows(new_table_data)
    delta_result = new_table.compare_with(old_table)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == result


def test_filtering_node_no_paths():
    filled_root = _create_filled_tree()
    assert filled_root.get_filtered_node([]).is_empty()


def test_filtering_node_wrong_node():
    filled_root = _create_filled_tree()
    filters = _make_filters([(["path", "to", "nta", "ta"], None)])
    filtered = filled_root.get_filtered_node(filters)
    assert filtered.get_node(["path", "to", "nta", "na"]) is None
    assert filtered.get_node(["path", "to", "nta", "nt"]) is None


def test_filtering_node_paths_no_keys():
    filled_root = _create_filled_tree()
    filters = _make_filters([(["path", "to", "nta", "ta"], None)])
    filtered_node = filled_root.get_filtered_node(filters).get_node(["path", "to", "nta", "ta"])
    assert filtered_node is not None

    assert not filtered_node.attributes.is_empty()
    assert filtered_node.attributes.pairs == {"ta0": "TA 0", "ta1": "TA 1"}

    assert not filtered_node.table.is_empty()
    assert filtered_node.table.rows == [
        {
            "ta0": "TA 00",
            "ta1": "TA 01"
        },
        {
            "ta0": "TA 10",
            "ta1": "TA 11"
        },
    ]


def test_filtering_node_paths_and_keys():
    filled_root = _create_filled_tree()
    filters = _make_filters([(["path", "to", "nta", "ta"], ["ta0"])])
    filtered_node = filled_root.get_filtered_node(filters).get_node(["path", "to", "nta", "ta"])
    assert filtered_node is not None

    assert not filtered_node.attributes.is_empty()
    assert filtered_node.attributes.pairs == {"ta0": "TA 0"}

    assert not filtered_node.table.is_empty()
    assert filtered_node.table.rows == [
        {
            "ta0": "TA 00",
        },
        {
            "ta0": "TA 10",
        },
    ]


def test_filtering_node_mixed():
    filled_root = _create_filled_tree()
    another_node1 = filled_root.setdefault_node(["path", "to", "another", "node1"])
    another_node1.attributes.add_pairs({"ak11": "Another value 11", "ak12": "Another value 12"})

    another_node2 = filled_root.setdefault_node(["path", "to", "another", "node2"])
    another_node2.table.add_rows([
        {
            "ak21": "Another value 211",
            "ak22": "Another value 212",
        },
        {
            "ak21": "Another value 221",
            "ak22": "Another value 222",
        },
    ])

    filters = _make_filters([
        (["path", "to", "another"], None),
        (["path", "to", "nta", "ta"], ["ta0"]),
    ])
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

TEST_DIR = "%s/tests/unit/cmk/utils/structured_data/tree_test_data" % cmk_path()

TEST_DATA_STORE = StructuredDataStore(Path(TEST_DIR))

tree_name_old_addresses_arrays_memory = HostName("tree_old_addresses_arrays_memory")
tree_name_old_addresses = HostName("tree_old_addresses")
tree_name_old_arrays = HostName("tree_old_arrays")
tree_name_old_interfaces = HostName("tree_old_interfaces")
tree_name_old_memory = HostName("tree_old_memory")
tree_name_old_heute = HostName("tree_old_heute")

tree_name_new_addresses_arrays_memory = HostName("tree_new_addresses_arrays_memory")
tree_name_new_addresses = HostName("tree_new_addresses")
tree_name_new_arrays = HostName("tree_new_arrays")
tree_name_new_interfaces = HostName("tree_new_interfaces")
tree_name_new_memory = HostName("tree_new_memory")
tree_name_new_heute = HostName("tree_new_heute")

old_trees = [
    tree_name_old_addresses_arrays_memory,
    tree_name_old_addresses,
    tree_name_old_arrays,
    tree_name_old_interfaces,
    tree_name_old_memory,
    tree_name_old_heute,
]
new_trees = [
    tree_name_new_addresses_arrays_memory,
    tree_name_new_addresses,
    tree_name_new_arrays,
    tree_name_new_interfaces,
    tree_name_new_memory,
    tree_name_new_heute,
]


def test_real_get_dict():
    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_dict("")
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_dict(0)  # type: ignore[arg-type]
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_dict(100)  # type: ignore[arg-type]
    assert 'Wrong tree path format' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_dict("a?")
    assert 'No valid tree path' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_dict("a$.")
    assert 'Specified tree path contains unexpected characters' in "%s" % e

    assert StructuredDataNode().get_dict("a.") == {}


def test_real_get_list():
    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_list("")
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_list(0)  # type: ignore[arg-type]
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_list(100)  # type: ignore[arg-type]
    assert 'Wrong tree path format' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_list("a?")
    assert 'No valid tree path' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataNode().get_list("a$.")
    assert 'Specified tree path contains unexpected characters' in "%s" % e

    assert StructuredDataNode().get_list("a:") == []


@pytest.mark.parametrize("tree_name", old_trees + new_trees)
def test_structured_data_StructuredDataTree_load_from(tree_name: HostName):
    TEST_DATA_STORE.load(host_name=tree_name)


def test_real_save_gzip(tmp_path):
    host_name = HostName("heute")
    target = tmp_path / str(host_name)
    raw_tree = {
        "node": {
            "foo": 1,
            "bär": 2,
        },
    }
    tree = StructuredDataNode.deserialize(raw_tree)
    store = StructuredDataStore(tmp_path)
    store.save(host_name=host_name, tree=tree)

    assert target.exists()

    gzip_filepath = target.with_suffix('.gz')
    assert gzip_filepath.exists()

    with gzip.open(str(gzip_filepath), 'rb') as f:
        f.read()


tree_old_addresses_arrays_memory = TEST_DATA_STORE.load(
    host_name=HostName("tree_old_addresses_arrays_memory"))
tree_old_addresses = TEST_DATA_STORE.load(host_name=HostName("tree_old_addresses"))
tree_old_arrays = TEST_DATA_STORE.load(host_name=HostName("tree_old_arrays"))
tree_old_interfaces = TEST_DATA_STORE.load(host_name=HostName("tree_old_interfaces"))
tree_old_memory = TEST_DATA_STORE.load(host_name=HostName("tree_old_memory"))
tree_old_heute = TEST_DATA_STORE.load(host_name=HostName("tree_old_heute"))

tree_new_addresses_arrays_memory = TEST_DATA_STORE.load(
    host_name=HostName("tree_new_addresses_arrays_memory"))
tree_new_addresses = TEST_DATA_STORE.load(host_name=HostName("tree_new_addresses"))
tree_new_arrays = TEST_DATA_STORE.load(host_name=HostName("tree_new_arrays"))
tree_new_interfaces = TEST_DATA_STORE.load(host_name=HostName("tree_new_interfaces"))
tree_new_memory = TEST_DATA_STORE.load(host_name=HostName("tree_new_memory"))
tree_new_heute = TEST_DATA_STORE.load(host_name=HostName("tree_new_heute"))

# Must have same order as tree_new
trees_old = [
    tree_old_addresses_arrays_memory,
    tree_old_addresses,
    tree_old_arrays,
    tree_old_interfaces,
    tree_old_memory,
    tree_old_heute,
]

# Must have same order as tree_old
trees_new = [
    tree_new_addresses_arrays_memory,
    tree_new_addresses,
    tree_new_arrays,
    tree_new_interfaces,
    tree_new_memory,
    tree_new_heute,
]

trees = trees_old + trees_new


def test_real_is_empty():
    assert StructuredDataNode().is_empty() is True


@pytest.mark.parametrize("tree", trees)
def test_real_is_empty_trees(tree):
    assert not tree.is_empty()


@pytest.mark.parametrize("tree_x", trees)
@pytest.mark.parametrize("tree_y", trees)
def test_real_is_equal(tree_x, tree_y):
    if id(tree_x) == id(tree_y):
        assert tree_x.is_equal(tree_y)
    else:
        assert not tree_x.is_equal(tree_y)


def test_real_equal_tables():
    tree_addresses_ordered = TEST_DATA_STORE.load(host_name=HostName("tree_addresses_ordered"))
    tree_addresses_unordered = TEST_DATA_STORE.load(host_name=HostName("tree_addresses_unordered"))

    assert tree_addresses_ordered.is_equal(tree_addresses_unordered)
    assert tree_addresses_unordered.is_equal(tree_addresses_ordered)


@pytest.mark.parametrize("tree", trees[:1])
def test_real_is_equal_save_and_load(tree, tmp_path):
    store = StructuredDataStore(tmp_path)
    try:
        store.save(host_name=HostName("foo"), tree=tree)
        loaded_tree = store.load(host_name=HostName("foo"))
        assert tree.is_equal(loaded_tree)
    finally:
        shutil.rmtree(str(tmp_path))


@pytest.mark.parametrize("tree,result",
                         list(zip(trees, [
                             21,
                             9,
                             10,
                             6284,
                             2,
                             16654,
                             23,
                             8,
                             10,
                             6185,
                             2,
                             16653,
                         ])))
def test_real_count_entries(tree, result):
    assert tree.count_entries() == result


@pytest.mark.parametrize("tree", trees)
def test_real_compare_with_self(tree):
    delta_result = tree.compare_with(tree)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == (0, 0, 0)


@pytest.mark.parametrize("tree_old,tree_new,result",
                         list(
                             zip(trees_old, trees_new, [
                                 (3, 2, 1),
                                 (0, 2, 1),
                                 (2, 0, 2),
                                 (12, 3, 111),
                                 (1, 1, 1),
                                 (1, 1, 2),
                             ])))
def test_real_compare_with(tree_old, tree_new, result):
    delta_result = tree_new.compare_with(tree_old)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == result


@pytest.mark.parametrize("tree,edges_t,edges_f",
                         list(
                             zip(trees_old, [
                                 ["hardware", "networking"],
                                 ["networking"],
                                 ["hardware"],
                                 ["hardware", "software", "networking"],
                                 ["hardware"],
                                 ["hardware", "software", "networking"],
                             ], [
                                 ["", "foobar", "software"],
                                 ["", "foobar", "hardware", "software"],
                                 ["", "foobar", "software", "networking"],
                                 [
                                     "",
                                     "foobar",
                                 ],
                                 ["", "foobar", "software", "networking"],
                                 [
                                     "",
                                     "foobar",
                                 ],
                             ])))
def test_real_get_node(tree, edges_t, edges_f):
    for edge_t in edges_t:
        assert tree.get_node([edge_t]) is not None
    for edge_f in edges_f:
        assert tree.get_node([edge_f]) is None


@pytest.mark.parametrize("tree,len_children", list(zip(
    trees_old,
    [2, 1, 1, 3, 1, 3],
)))
def test_real_get_children(tree, len_children):
    tree_children = tree._nodes
    assert len(tree_children) == len_children


@pytest.mark.parametrize("tree_start,tree_edges", [
    (tree_old_addresses, [
        (tree_old_arrays, ["hardware", "networking"], [
            ("get_attributes", ["hardware", "memory", "arrays", "0"]),
            ("get_table", ["hardware", "memory", "arrays", "0", "devices"]),
            ("get_table", ["hardware", "memory", "arrays", "1", "others"]),
        ]),
        (tree_new_memory, ["hardware", "networking"], [
            ("get_attributes", ["hardware", "memory"]),
        ]),
        (tree_new_interfaces, ["hardware", "networking", "software"], [
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
        ])
    ]),
])
def test_real_merge_with_get_children(tree_start, tree_edges):
    for tree, edges, sub_children in tree_edges:
        tree_start.merge_with(tree)
        assert id(tree) == id(tree)
        assert tree.is_equal(tree)
        for edge in edges:
            assert tree_start.get_node([edge]) is not None
        for m_name, path in sub_children:
            m = getattr(tree_start, m_name)
            assert m is not None
            assert m(path) is not None


TREE_INV = TEST_DATA_STORE.load(host_name=HostName("tree_inv"))
TREE_STATUS = TEST_DATA_STORE.load(host_name=HostName("tree_status"))


@pytest.mark.parametrize("tree_inv,tree_status", [
    (TREE_INV, TREE_STATUS),
])
def test_real_merge_with_table(tree_inv, tree_status):
    tree_inv.merge_with(tree_status)
    assert 'foobar' in tree_inv.serialize()
    num = tree_inv.get_table(['foobar'])
    assert len(num.rows) == 5


@pytest.mark.parametrize(
    "tree,paths,unavail",
    [
        (
            tree_new_interfaces,
            # container                   table                    attributes
            [(["hardware", "components"], None), (["networking", "interfaces"], None),
             (["software", "os"], None)],
            [["hardware", "system"], ["software", "applications"]]),
    ])
def test_real_filtered_tree(tree, paths, unavail):
    filtered = tree.get_filtered_node(_make_filters(paths))
    assert id(tree) != id(filtered)
    assert not tree.is_equal(filtered)
    for path in unavail:
        assert filtered.get_node(path) is None


@pytest.mark.parametrize("tree,paths,amount_if_entries", [
    (tree_new_interfaces, [
        (['networking'], None),
    ], 3178),
    (tree_new_interfaces, [
        (['networking'], []),
    ], None),
    (tree_new_interfaces, [
        (['networking'], ['total_interfaces', 'total_ethernet_ports', 'available_ethernet_ports']),
    ], None),
    (tree_new_interfaces, [
        (['networking', 'interfaces'], None),
    ], 3178),
    (tree_new_interfaces, [
        (['networking', 'interfaces'], []),
    ], 3178),
    (tree_new_interfaces, [
        (['networking', 'interfaces'], ['admin_status']),
    ], 326),
    (tree_new_interfaces, [
        (['networking', 'interfaces'], ['admin_status', 'FOOBAR']),
    ], 326),
    (tree_new_interfaces, [
        (['networking', 'interfaces'], ['admin_status', 'oper_status']),
    ], 652),
    (tree_new_interfaces, [
        (['networking', 'interfaces'], ['admin_status', 'oper_status', 'FOOBAR']),
    ], 652),
])
def test_real_filtered_tree_networking(tree, paths, amount_if_entries):
    the_paths = list(paths)
    filtered = tree.get_filtered_node(_make_filters(paths))
    assert the_paths == paths
    assert filtered.get_node(['networking']) is not None
    assert filtered.get_node(['hardware']) is None
    assert filtered.get_node(['software']) is None

    if amount_if_entries is not None:
        interfaces = filtered.get_table(['networking', 'interfaces'])
        assert interfaces.count_entries() == amount_if_entries


def test_real_building_tree():
    def plugin_dict():
        node = struct_tree.get_dict("level0_0.level1_dict.")
        for a, b in [("d1", "D1"), ("d2", "D2")]:
            node.setdefault(a, b)

    def plugin_list():
        node = struct_tree.get_list("level0_1.level1_list:")
        for a, b in [("l1", "L1"), ("l2", "L2")]:
            node.append({a: b})

    def plugin_nested_list():
        node = struct_tree.get_list("level0_2.level1_nested_list:")
        for index in range(10):
            array: Dict[str, List[Dict[str, str]]] = {"foo": []}
            for a, b in [("nl1", "NL1"), ("nl2", "NL2")]:
                array["foo"].append({a: "%s-%s" % (b, index)})
            node.append(array)

    struct_tree = StructuredDataNode()
    plugin_dict()
    plugin_list()
    plugin_nested_list()
    struct_tree.normalize_nodes()

    assert struct_tree.get_node(["level0_0"]) is not None
    assert struct_tree.get_node(["level0_1"]) is not None
    assert struct_tree.get_node(["level0_2"]) is not None
    assert struct_tree.get_node(["foobar"]) is None

    level1_dict = struct_tree.get_attributes(["level0_0", "level1_dict"])
    level1_list = struct_tree.get_table(["level0_1", "level1_list"])
    level1_nested_list_con = struct_tree.get_node(["level0_2", "level1_nested_list"])
    level1_nested_list_num = struct_tree.get_table(["level0_2", "level1_nested_list"])
    level1_nested_list_att = struct_tree.get_attributes(["level0_2", "level1_nested_list"])

    assert isinstance(level1_dict, Attributes)
    assert 'd1' in level1_dict.pairs
    assert 'd2' in level1_dict.pairs

    assert isinstance(level1_list, Table)
    known_keys = [key for row in level1_list.rows for key in row]
    assert 'l1' in known_keys
    assert 'l2' in known_keys
    assert level1_nested_list_num is not None and level1_nested_list_num.is_empty()
    assert level1_nested_list_att is not None and level1_nested_list_att.is_empty()

    assert isinstance(level1_nested_list_con, StructuredDataNode)
    assert list(level1_nested_list_con._nodes) == ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


@pytest.mark.parametrize("zipped_trees", list(zip(old_trees, new_trees)))
def test_delta_structured_data_tree_serialization(zipped_trees):
    old_filename, new_filename = zipped_trees

    old_tree = TEST_DATA_STORE.load(host_name=old_filename)
    new_tree = TEST_DATA_STORE.load(host_name=new_filename)
    delta_result = old_tree.compare_with(new_tree)

    delta_raw_tree = delta_result.delta.serialize()
    assert isinstance(delta_raw_tree, dict)
    new_delta_tree = StructuredDataNode.deserialize(delta_raw_tree)

    assert delta_result.delta.is_equal(new_delta_tree)


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
        ((["path", "to", "node"], None), ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=True,
             attributes=True,
             restricted_attributes=True,
             columns=True,
             restricted_columns=True,
         )),
        ((["path", "to", "node"], []), ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=False,
             restricted_nodes=False,
             attributes=True,
             restricted_attributes=True,
             columns=True,
             restricted_columns=True,
         )),
        ((["path", "to", "node"], ["key"]), ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=False,
             restricted_nodes=False,
             attributes=True,
             restricted_attributes=False,
             columns=True,
             restricted_columns=False,
         )),
        # Dict format
        ({
            "visible_raw_path": "path.to.node",
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=True,
             attributes=True,
             restricted_attributes=True,
             columns=True,
             restricted_columns=True,
         )),
        ({
            "visible_raw_path": "path.to.node",
            "nodes": ("choices", ["node"]),
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=False,
             attributes=True,
             restricted_attributes=True,
             columns=True,
             restricted_columns=True,
         )),
        ({
            "visible_raw_path": "path.to.node",
            "attributes": ("choices", ["key"]),
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=True,
             attributes=True,
             restricted_attributes=False,
             columns=True,
             restricted_columns=True,
         )),
        ({
            "visible_raw_path": "path.to.node",
            "columns": ("choices", ["key"]),
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=True,
             attributes=True,
             restricted_attributes=True,
             columns=True,
             restricted_columns=False,
         )),
        ({
            "visible_raw_path": "path.to.node",
            "nodes": "nothing"
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=False,
             restricted_nodes=False,
             attributes=True,
             restricted_attributes=True,
             columns=True,
             restricted_columns=True,
         )),
        ({
            "visible_raw_path": "path.to.node",
            "attributes": "nothing",
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=True,
             attributes=False,
             restricted_attributes=False,
             columns=True,
             restricted_columns=True,
         )),
        ({
            "visible_raw_path": "path.to.node",
            "columns": "nothing",
        }, ["path", "to", "node"],
         ExpectedFilterResults(
             nodes=True,
             restricted_nodes=True,
             attributes=True,
             restricted_attributes=True,
             columns=False,
             restricted_columns=False,
         )),
    ])
def test_make_filter(entry, expected_path, expected_filter_results):
    f = make_filter(entry)

    assert f.path == expected_path

    assert f.filter_nodes("node") is expected_filter_results.nodes
    assert f.filter_nodes("other") is expected_filter_results.restricted_nodes

    assert f.filter_attributes("key") is expected_filter_results.attributes
    assert f.filter_attributes("other") is expected_filter_results.restricted_attributes

    assert f.filter_columns("key") is expected_filter_results.columns
    assert f.filter_columns("other") is expected_filter_results.restricted_columns


# Test helper


@pytest.mark.parametrize("raw_path, expected_path", [
    ("", []),
    ("path.to.node_1", ["path", "to", "node_1"]),
])
def test_parse_visible_tree_path(raw_path, expected_path):
    assert parse_visible_raw_path(raw_path) == expected_path


def test__is_table():
    raw_tree = {
        "path-to": {
            "idx-node": [{
                "idx-attr": "value",
                "idx-table": [{
                    "idx-col": "value"
                }],
                "idx-sub-node": {
                    "foo-node": {
                        "foo-attr": "value",
                    },
                },
                "idx-sub-idx-node": [{
                    "bar-node": {
                        "bar-attr": "value",
                    },
                },]
            },],
            "node": {
                "attr": "value"
            },
            "table": [{
                "col": "value"
            }],
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

    idx_node_attr = tree.get_node(["path-to", "idx-node", "0"])
    assert idx_node_attr is not None
    assert idx_node_attr.attributes.pairs == {'idx-attr': 'value'}
    assert idx_node_attr.table.rows == []

    idx_sub_idx_node_attr = tree.get_node(
        ["path-to", "idx-node", "0", "idx-sub-idx-node", "0", "bar-node"])
    assert idx_sub_idx_node_attr is not None
    assert idx_sub_idx_node_attr.attributes.pairs == {'bar-attr': 'value'}
    assert idx_sub_idx_node_attr.table.rows == []

    idx_sub_node_attr = tree.get_node(["path-to", "idx-node", "0", "idx-sub-node", "foo-node"])
    assert idx_sub_node_attr is not None
    assert idx_sub_node_attr.attributes.pairs == {'foo-attr': 'value'}
    assert idx_sub_node_attr.table.rows == []

    idx_table = tree.get_node(["path-to", "idx-node", "0", "idx-table"])
    assert idx_table is not None
    assert idx_table.attributes.pairs == {}
    assert idx_table.table.rows == [{'idx-col': 'value'}]

    attr_node = tree.get_node(["path-to", "node"])
    assert attr_node is not None
    assert attr_node.attributes.pairs == {"attr": "value"}
    assert attr_node.table.rows == []

    table_node = tree.get_node(["path-to", "table"])
    assert table_node is not None
    assert table_node.attributes.pairs == {}
    assert table_node.table.rows == [{"col": "value"}]
