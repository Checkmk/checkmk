#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List

import shutil
import pytest
from pathlib import Path
import gzip

from testlib import cmk_path

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.structured_data import (
    StructuredDataNode,
    Attributes,
    Table,
    load_tree_from,
    save_tree_to,
)

#   .--NodeAttribute-------------------------------------------------------.
#   |  _   _           _         _   _   _        _ _           _          |
#   | | \ | | ___   __| | ___   / \ | |_| |_ _ __(_) |__  _   _| |_ ___    |
#   | |  \| |/ _ \ / _` |/ _ \ / _ \| __| __| '__| | '_ \| | | | __/ _ \   |
#   | | |\  | (_) | (_| |  __// ___ \ |_| |_| |  | | |_) | |_| | ||  __/   |
#   | |_| \_|\___/ \__,_|\___/_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mk_root():
    root = StructuredDataNode()
    node_0 = root.setdefault_node(["0_cna"])
    node_0.setdefault_node(["1_cn"])
    node_0.setdefault_node(["1_ca"])
    return root


def mk_filled_root():
    root = StructuredDataNode()
    node_1 = root.setdefault_node(["0_cna", "1_cn"])
    node_2 = root.setdefault_node(["0_cna", "1_ca"])
    node_3 = root.setdefault_node(["0_cna", "1_na"])
    node_4 = root.setdefault_node(["0_cna", "1_cn", "2_n"])
    node_5 = root.setdefault_node(["0_cna", "1_ca", "2_a"])

    node_1.add_table([{"n10": "N-1-0"}])
    node_2.add_attributes({"a10": "A-1-0"})
    node_3.add_table([{"n20": "N-2-0"}, {"n21": "N-2-1"}])
    node_3.add_attributes({"a20": "A-2-0", "a21": "A-1-1"})
    node_4.add_table([{"n30": "N-3-0"}, {"n31": "N-3-1"}, {"n32": "N-3-2"}])
    node_5.add_attributes({"a30": "A-3-0", "a31": "A-3-1", "a32": "A-3-2"})
    return root


def test_structured_data_NodeAttribute():
    mk_root()
    mk_filled_root()


node_attributes = [
    mk_root(),
    mk_filled_root(),
]


@pytest.mark.parametrize("node_attribute", [mk_root()])
def test_structured_data_NodeAttribute_is_empty(node_attribute):
    assert node_attribute.is_empty()


@pytest.mark.parametrize("node_attribute", [mk_filled_root()])
def test_structured_data_NodeAttribute_is_empty_false(node_attribute):
    assert not node_attribute.is_empty()


@pytest.mark.parametrize("na_x", node_attributes)
@pytest.mark.parametrize("na_y", node_attributes)
def test_structured_data_NodeAttribute_is_equal(na_x, na_y):
    if id(na_x) == id(na_y):
        assert na_x.is_equal(na_y)
    else:
        assert not na_x.is_equal(na_y)


@pytest.mark.parametrize("node_attribute,result", list(zip(node_attributes, [0, 12])))
def test_structured_data_NodeAttribute_count_entries(node_attribute, result):
    assert node_attribute.count_entries() == result


@pytest.mark.parametrize("na_old,na_new,result", [(mk_root(), mk_filled_root(), (12, 0, 0))])
def test_structured_data_NodeAttribute_compare_with(na_old, na_new, result):
    delta_result = na_new.compare_with(na_old)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == result
    if result == (0, 0, 0):
        assert delta_result.delta.is_empty()
    else:
        assert not delta_result.delta.is_empty()


@pytest.mark.parametrize("old_table_data,new_table_data,result", [
    ([], [], (0, 0, 0)),
    ([{
        "id": "1",
        "val": 0
    }], [], (0, 0, 1)),
    ([], [{
        "id": "1",
        "val": 0
    }], (1, 0, 0)),
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
    }], (0, 0, 1)),
    ([{
        "id": "1",
        "val": 0
    }], [{
        "id": "1",
        "val": 0
    }, {
        "id": "2",
        "val": 1
    }], (1, 0, 0)),
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
    }], (4, 0, 3)),
])
def test_structured_data_Table_compare_with(old_table_data, new_table_data, result):
    old_table = Table()
    old_table.add_table(old_table_data)
    new_table = Table()
    new_table.add_table(new_table_data)
    delta_result = new_table.compare_with(old_table)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == result


@pytest.mark.parametrize("node_attribute,edge", [
    (mk_root(), "0_cna"),
])
def test_structured_data_NodeAttribute_has_edge(node_attribute, edge):
    assert node_attribute.has_edge(edge)
    assert not node_attribute.has_edge("REALLY NO EDGE")


#.
#   .--Structured DataTree-------------------------------------------------.
#   |         ____  _                   _                      _           |
#   |        / ___|| |_ _ __ _   _  ___| |_ _   _ _ __ ___  __| |          |
#   |        \___ \| __| '__| | | |/ __| __| | | | '__/ _ \/ _` |          |
#   |         ___) | |_| |  | |_| | (__| |_| |_| | | |  __/ (_| |          |
#   |        |____/ \__|_|   \__,_|\___|\__|\__,_|_|  \___|\__,_|          |
#   |                                                                      |
#   |               ____        _       _____                              |
#   |              |  _ \  __ _| |_ __ |_   _| __ ___  ___                 |
#   |              | | | |/ _` | __/ _` || || '__/ _ \/ _ \                |
#   |              | |_| | (_| | || (_| || || | |  __/  __/                |
#   |              |____/ \__,_|\__\__,_||_||_|  \___|\___|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

TEST_DIR = "%s/tests/unit/cmk/utils/structured_data/tree_test_data" % cmk_path()

tree_name_old_addresses_arrays_memory = "%s/tree_old_addresses_arrays_memory" % TEST_DIR
tree_name_old_addresses = "%s/tree_old_addresses" % TEST_DIR
tree_name_old_arrays = "%s/tree_old_arrays" % TEST_DIR
tree_name_old_interfaces = "%s/tree_old_interfaces" % TEST_DIR
tree_name_old_memory = "%s/tree_old_memory" % TEST_DIR
tree_name_old_heute = "%s/tree_old_heute" % TEST_DIR

tree_name_new_addresses_arrays_memory = "%s/tree_new_addresses_arrays_memory" % TEST_DIR
tree_name_new_addresses = "%s/tree_new_addresses" % TEST_DIR
tree_name_new_arrays = "%s/tree_new_arrays" % TEST_DIR
tree_name_new_interfaces = "%s/tree_new_interfaces" % TEST_DIR
tree_name_new_memory = "%s/tree_new_memory" % TEST_DIR
tree_name_new_heute = "%s/tree_new_heute" % TEST_DIR

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


def test_structured_data_StructuredDataNode_get_dict():
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


def test_structured_data_StructuredDataNode_get_list():
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
def test_structured_data_StructuredDataNode_load_tree_from(tree_name):
    load_tree_from(tree_name)


def test_structured_data_StructuredDataNode_save_gzip(tmp_path):
    filename = "heute"
    target = Path(tmp_path).joinpath(filename)
    raw_tree = {
        "node": {
            "foo": 1,
            "bär": 2,
        },
    }
    tree = StructuredDataNode().create_tree_from_raw_tree(raw_tree)

    save_tree_to(tree, tmp_path, filename)

    assert target.exists()

    gzip_filepath = target.with_suffix('.gz')
    assert gzip_filepath.exists()

    with gzip.open(str(gzip_filepath), 'rb') as f:
        f.read()


tree_old_addresses_arrays_memory = load_tree_from(tree_name_old_addresses_arrays_memory)
tree_old_addresses = load_tree_from(tree_name_old_addresses)
tree_old_arrays = load_tree_from(tree_name_old_arrays)
tree_old_interfaces = load_tree_from(tree_name_old_interfaces)
tree_old_memory = load_tree_from(tree_name_old_memory)
tree_old_heute = load_tree_from(tree_name_old_heute)

tree_new_addresses_arrays_memory = load_tree_from(tree_name_new_addresses_arrays_memory)
tree_new_addresses = load_tree_from(tree_name_new_addresses)
tree_new_arrays = load_tree_from(tree_name_new_arrays)
tree_new_interfaces = load_tree_from(tree_name_new_interfaces)
tree_new_memory = load_tree_from(tree_name_new_memory)
tree_new_heute = load_tree_from(tree_name_new_heute)

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


def test_structured_data_StructuredDataNode_is_empty():
    assert StructuredDataNode().is_empty() is True


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataNode_is_empty_trees(tree):
    assert not tree.is_empty()


@pytest.mark.parametrize("tree_x", trees)
@pytest.mark.parametrize("tree_y", trees)
def test_structured_data_StructuredDataNode_is_equal(tree_x, tree_y):
    if id(tree_x) == id(tree_y):
        assert tree_x.is_equal(tree_y)
    else:
        assert not tree_x.is_equal(tree_y)


def test_structured_data_StructuredDataNode_equal_tables():
    tree_addresses_ordered = load_tree_from("%s/tree_addresses_ordered" % TEST_DIR)
    tree_addresses_unordered = load_tree_from("%s/tree_addresses_unordered" % TEST_DIR)
    assert tree_addresses_ordered.is_equal(tree_addresses_unordered)
    assert tree_addresses_unordered.is_equal(tree_addresses_ordered)


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataTree_is_equal_save_and_load(tree, tmp_path):
    try:
        save_tree_to(tree, str(tmp_path), "foo", False)
        loaded_tree = load_tree_from(str(tmp_path / "foo"))
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
def test_structured_data_StructuredDataNode_count_entries(tree, result):
    assert tree.count_entries() == result


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataNode_compare_with_self(tree):
    delta_result = tree.compare_with(tree)
    assert (delta_result.counter['new'], delta_result.counter['changed'],
            delta_result.counter['removed']) == (0, 0, 0)


@pytest.mark.parametrize("tree_old,tree_new,result",
                         list(
                             zip(trees_old, trees_new, [
                                 (2, 2, 1),
                                 (0, 2, 1),
                                 (1, 0, 1),
                                 (2, 3, 16),
                                 (1, 1, 1),
                                 (1, 1, 2),
                             ])))
def test_structured_data_StructuredDataNode_compare_with(tree_old, tree_new, result):
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
def test_structured_data_StructuredDataNode_has_edge(tree, edges_t, edges_f):
    for edge_t in edges_t:
        assert tree.has_edge(edge_t)
    for edge_f in edges_f:
        assert not tree.has_edge(edge_f)


@pytest.mark.parametrize("tree,len_children", list(zip(
    trees_old,
    [2, 1, 1, 3, 1, 3],
)))
def test_structured_data_StructuredDataNode_get_children(tree, len_children):
    tree_children = tree._nodes
    assert len(tree_children) == len_children


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataNode_copy(tree):
    copied = tree.copy()
    assert id(tree) != id(copied)
    assert tree.is_equal(copied)


@pytest.mark.parametrize("tree_start,tree_edges", [
    (tree_old_addresses, [
        (tree_old_arrays, ["hardware", "networking"], [
            ("get_attributes", ["hardware", "memory", "arrays", 0]),
            ("get_table", ["hardware", "memory", "arrays", 0, "devices"]),
            ("get_table", ["hardware", "memory", "arrays", 1, "others"]),
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
def test_structured_data_StructuredDataNode_merge_with_get_children(tree_start, tree_edges):
    tree_start = tree_start.copy()
    for tree, edges, sub_children in tree_edges:
        tree_start.merge_with(tree)
        assert id(tree) == id(tree)
        assert tree.is_equal(tree)
        for edge in edges:
            assert tree_start.has_edge(edge)
        for m_name, path in sub_children:
            m = getattr(tree_start, m_name)
            assert m is not None
            assert m(path) is not None


TREE_INV = load_tree_from("%s/tree_inv" % TEST_DIR)
TREE_STATUS = load_tree_from("%s/tree_status" % TEST_DIR)


@pytest.mark.parametrize("tree_inv,tree_status", [
    (TREE_INV, TREE_STATUS),
])
def test_structured_data_StructuredDataNode_merge_with_table(tree_inv, tree_status):
    tree_inv.merge_with(tree_status)
    assert 'foobar' in tree_inv.get_raw_tree()
    num = tree_inv.get_table(['foobar'])
    assert len(num.data) == 5


@pytest.mark.parametrize(
    "tree,paths,unavail",
    [
        (
            tree_new_interfaces,
            # node                   table                    attributes
            [(["hardware", "components"], None), (["networking", "interfaces"], None),
             (["software", "os"], None)],
            [["hardware", "system"], ["software", "applications"]]),
    ])
def test_structured_data_StructuredDataNode_filtered_tree(tree, paths, unavail):
    filtered = tree.get_filtered_node(paths)
    assert id(tree) != id(filtered)
    assert not tree.is_equal(filtered)
    for path in unavail:
        assert filtered.get_node(path) is None


@pytest.mark.parametrize("tree,paths,amount_if_entries", [
    (tree_new_interfaces, [(['networking'], None)], 3178),
    (tree_new_interfaces, [(['networking'], [])], None),
    (tree_new_interfaces, [
        (['networking'], ['total_interfaces', 'total_ethernet_ports', 'available_ethernet_ports'])
    ], None),
    (tree_new_interfaces, [(['networking', 'interfaces'], None)], 3178),
    (tree_new_interfaces, [(['networking', 'interfaces'], [])], 3178),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status'])], 326),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status', 'FOOBAR'])], 326),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status', 'oper_status'])], 652),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status', 'oper_status', 'FOOBAR'])
                          ], 652),
])
def test_structured_data_StructuredDataNode_filtered_tree_networking(tree, paths,
                                                                     amount_if_entries):
    the_paths = list(paths)
    filtered = tree.get_filtered_node(paths)
    assert the_paths == paths
    assert filtered.has_edge('networking')
    assert not filtered.has_edge('hardware')
    assert not filtered.has_edge('software')

    interfaces = filtered.get_table(['networking', 'interfaces'])
    if interfaces is not None:
        assert bool(interfaces)
        assert interfaces.count_entries() == amount_if_entries


def test_structured_data_StructuredDataNode_building_tree():
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

    assert struct_tree.has_edge("level0_0")
    assert struct_tree.has_edge("level0_1")
    assert struct_tree.has_edge("level0_2")
    assert not struct_tree.has_edge("foobar")

    level1_dict = struct_tree.get_attributes(["level0_0", "level1_dict"])
    level1_list = struct_tree.get_table(["level0_1", "level1_list"])
    level1_nested_list_con = struct_tree.get_node(["level0_2", "level1_nested_list"])
    level1_nested_list_num = struct_tree.get_table(["level0_2", "level1_nested_list"])
    level1_nested_list_att = struct_tree.get_attributes(["level0_2", "level1_nested_list"])

    assert isinstance(level1_dict, Attributes)
    assert 'd1' in level1_dict.data
    assert 'd2' in level1_dict.data

    assert isinstance(level1_list, Table)
    known_keys = [key for row in level1_list.data for key in row]
    assert 'l1' in known_keys
    assert 'l2' in known_keys
    assert level1_nested_list_num is not None and level1_nested_list_num.is_empty()
    assert level1_nested_list_att is not None and level1_nested_list_att.is_empty()

    assert isinstance(level1_nested_list_con, StructuredDataNode)
    assert list(level1_nested_list_con._nodes) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.parametrize("zipped_trees", list(zip(old_trees, new_trees)))
def test_delta_structured_data_tree_serialization(zipped_trees):
    old_tree = StructuredDataNode()
    new_tree = StructuredDataNode()

    old_filename, new_filename = zipped_trees

    old_tree = load_tree_from(old_filename)
    new_tree = load_tree_from(new_filename)
    delta_result = old_tree.compare_with(new_tree)

    new_delta_tree = StructuredDataNode()
    raw_delta_tree = delta_result.delta.get_raw_tree()
    assert isinstance(raw_delta_tree, dict)
    new_delta_tree.create_tree_from_raw_tree(raw_delta_tree)

    assert delta_result.delta.is_equal(new_delta_tree)
