#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List

import shutil
import pytest  # type: ignore[import]
from pathlib import Path
import gzip

from testlib import cmk_path  # type: ignore[import]

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.structured_data import StructuredDataTree, Container, Attributes, Numeration

# Convention: test functions are named like
#   test_structured_data_INFIX_METHODNAME where
#   INFIX in [NodeAttribute, StructuredDataTree,]

# TODO functions to test
# egrep "    def\s*[^_]|\s*class" lib/structured_data.py | grep -v "__init__" > ~/playground/inventory/functions_to_test

#   .--NodeAttribute-------------------------------------------------------.
#   |  _   _           _         _   _   _        _ _           _          |
#   | | \ | | ___   __| | ___   / \ | |_| |_ _ __(_) |__  _   _| |_ ___    |
#   | |  \| |/ _ \ / _` |/ _ \ / _ \| __| __| '__| | '_ \| | | | __/ _ \   |
#   | | |\  | (_) | (_| |  __// ___ \ |_| |_| |  | | |_) | |_| | ||  __/   |
#   | |_| \_|\___/ \__,_|\___/_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mk_root():
    # This tree contains all possibilities:
    # {'0_cna': {'__Att__': '{:}',
    #            '__Con__': {'1_ca': {'__Att__': '{:}',
    #                                 '__Con__': {'2_a': {'__Att__': '{:}',
    #                                                     '__path__': ('0_cna',
    #                                                                  '1_ca',
    #                                                                  '2_a')}},
    #                                 '__path__': ('0_cna', '1_ca')},
    #                        '1_cn': {'__Con__': {'2_n': {'__Num__': '[:]',
    #                                                     '__path__': ('0_cna',
    #                                                                  '1_ca',
    #                                                                  '2_n')}},
    #                                 '__Num__': '[:]',
    #                                 '__path__': ('0_cna', '1_cn')},
    #                        '1_na': {'__Att__': '{:}',
    #                                 '__Num__': '[:]',
    #                                 '__path__': ('0_cna', '1_na')}},
    #            '__Num__': '[:]',
    #            '__path__': ('0_cna',)}}
    root = Container()
    container_0 = Container()
    numeration_0 = Numeration()
    attributes_0 = Attributes()
    root.add_child("0_cna", container_0, ("0_cna",))
    root.add_child("0_cna", numeration_0, ("0_cna",))
    root.add_child("0_cna", attributes_0, ("0_cna",))

    numeration_1 = Numeration()
    container_1 = Container()
    container_0.add_child("1_cn", numeration_1, ("0_cna", "1_cn"))
    container_0.add_child("1_cn", container_1, ("0_cna", "1_cn"))

    attributes_1 = Attributes()
    container_2 = Container()
    container_0.add_child("1_ca", attributes_1, ("0_cna", "1_ca"))
    container_0.add_child("1_ca", container_2, ("0_cna", "1_ca"))

    numeration_2 = Numeration()
    attributes_2 = Attributes()
    container_0.add_child("1_na", numeration_2, ("0_cna", "1_na"))
    container_0.add_child("1_na", attributes_2, ("0_cna", "1_na"))

    numeration_3 = Numeration()
    attributes_3 = Attributes()
    container_1.add_child("2_n", numeration_3, ("0_cna", "1_ca", "2_n"))
    container_2.add_child("2_a", attributes_3, ("0_cna", "1_ca", "2_a"))
    return root


def mk_filled_root():
    root = Container()
    container_0 = Container()
    numeration_0 = Numeration()
    attributes_0 = Attributes()
    root.add_child("0_cna", container_0, ("0_cna",))
    root.add_child("0_cna", numeration_0, ("0_cna",))
    root.add_child("0_cna", attributes_0, ("0_cna",))

    numeration_1 = Numeration()
    numeration_1.set_child_data([{"n10": "N-1-0"}])
    container_1 = Container()
    container_0.add_child("1_cn", numeration_1, ("0_cna", "1_cn"))
    container_0.add_child("1_cn", container_1, ("0_cna", "1_cn"))

    attributes_1 = Attributes()
    attributes_1.set_child_data({"a10": "A-1-0"})
    container_2 = Container()
    container_0.add_child("1_ca", attributes_1, ("0_cna", "1_ca"))
    container_0.add_child("1_ca", container_2, ("0_cna", "1_ca"))

    numeration_2 = Numeration()
    numeration_2.set_child_data([{"n20": "N-2-0"}, {"n21": "N-2-1"}])
    attributes_2 = Attributes()
    attributes_2.set_child_data({"a20": "A-2-0", "a21": "A-1-1"})
    container_0.add_child("1_na", numeration_2, ("0_cna", "1_na"))
    container_0.add_child("1_na", attributes_2, ("0_cna", "1_na"))

    numeration_3 = Numeration()
    numeration_3.set_child_data([{"n30": "N-3-0"}, {"n31": "N-3-1"}, {"n32": "N-3-2"}])
    attributes_3 = Attributes()
    attributes_3.set_child_data({"a30": "A-3-0", "a31": "A-3-1", "a32": "A-3-2"})
    container_1.add_child("2_n", numeration_3, ("0_cna", "1_ca", "2_n"))
    container_2.add_child("2_a", attributes_3, ("0_cna", "1_ca", "2_a"))
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
    n, c, r, d = na_new.compare_with(na_old)
    assert (n, c, r) == result
    if result == (0, 0, 0):
        assert d.is_empty()
    else:
        assert not d.is_empty()


@pytest.mark.parametrize("old_numeration_data,new_numeration_data,result", [
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
def test_structured_data_Numeration_compare_with(old_numeration_data, new_numeration_data, result):
    old_numeration = Numeration()
    old_numeration.set_child_data(old_numeration_data)
    new_numeration = Numeration()
    new_numeration.set_child_data(new_numeration_data)
    n, c, r, _d = new_numeration.compare_with(old_numeration)
    assert (n, c, r) == result


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


def test_structured_data_StructuredDataTree_get_dict():
    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_dict("")
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_dict(0)
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_dict(100)
    assert 'Wrong tree path format' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_dict("a?")
    assert 'No valid tree path' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_dict("a$.")
    assert 'Specified tree path contains unexpected characters' in "%s" % e

    assert StructuredDataTree().get_dict("a.") == {}


def test_structured_data_StructuredDataTree_get_list():
    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_list("")
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_list(0)
    assert 'Empty tree path or zero' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_list(100)
    assert 'Wrong tree path format' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_list("a?")
    assert 'No valid tree path' in "%s" % e

    with pytest.raises(MKGeneralException) as e:
        StructuredDataTree().get_list("a$.")
    assert 'Specified tree path contains unexpected characters' in "%s" % e

    assert StructuredDataTree().get_list("a:") == []


@pytest.mark.parametrize("tree_name", old_trees + new_trees)
def test_structured_data_StructuredDataTree_load_from(tree_name):
    StructuredDataTree().load_from(tree_name)


def test_structured_data_StructuredDataTree_save_gzip(tmp_path):
    filename = "heute"
    target = Path(tmp_path).joinpath(filename)
    raw_tree = {
        "node": {
            "foo": 1,
            "bär": 2,
        },
    }
    tree = StructuredDataTree().create_tree_from_raw_tree(raw_tree)

    tree.save_to(tmp_path, filename)

    assert target.exists()

    gzip_filepath = target.with_suffix('.gz')
    assert gzip_filepath.exists()

    with gzip.open(str(gzip_filepath), 'rb') as f:
        f.read()


tree_old_addresses_arrays_memory = StructuredDataTree().load_from(
    tree_name_old_addresses_arrays_memory)
tree_old_addresses = StructuredDataTree().load_from(tree_name_old_addresses)
tree_old_arrays = StructuredDataTree().load_from(tree_name_old_arrays)
tree_old_interfaces = StructuredDataTree().load_from(tree_name_old_interfaces)
tree_old_memory = StructuredDataTree().load_from(tree_name_old_memory)
tree_old_heute = StructuredDataTree().load_from(tree_name_old_heute)

tree_new_addresses_arrays_memory = StructuredDataTree().load_from(
    tree_name_new_addresses_arrays_memory)
tree_new_addresses = StructuredDataTree().load_from(tree_name_new_addresses)
tree_new_arrays = StructuredDataTree().load_from(tree_name_new_arrays)
tree_new_interfaces = StructuredDataTree().load_from(tree_name_new_interfaces)
tree_new_memory = StructuredDataTree().load_from(tree_name_new_memory)
tree_new_heute = StructuredDataTree().load_from(tree_name_new_heute)

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


def test_structured_data_StructuredDataTree_is_empty():
    assert StructuredDataTree().is_empty() is True


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataTree_is_empty_trees(tree):
    assert not tree.is_empty()


@pytest.mark.parametrize("tree_x", trees)
@pytest.mark.parametrize("tree_y", trees)
def test_structured_data_StructuredDataTree_is_equal(tree_x, tree_y):
    if id(tree_x) == id(tree_y):
        assert tree_x.is_equal(tree_y)
    else:
        assert not tree_x.is_equal(tree_y)


def test_structured_data_StructuredDataTree_equal_numerations():
    tree_addresses_ordered = StructuredDataTree().load_from("%s/tree_addresses_ordered" % TEST_DIR)
    tree_addresses_unordered = StructuredDataTree().load_from("%s/tree_addresses_unordered" %
                                                              TEST_DIR)
    assert tree_addresses_ordered.is_equal(tree_addresses_unordered)
    assert tree_addresses_unordered.is_equal(tree_addresses_ordered)


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataTree_is_equal_save_and_load(tree, tmp_path):
    try:
        tree.save_to(str(tmp_path), "foo", False)
        loaded_tree = StructuredDataTree().load_from(str(tmp_path / "foo"))
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
def test_structured_data_StructuredDataTree_count_entries(tree, result):
    assert tree.count_entries() == result


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataTree_compare_with_self(tree):
    new, changed, removed, _delta = tree.compare_with(tree)
    assert (new, changed, removed) == (0, 0, 0)


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
def test_structured_data_StructuredDataTree_compare_with(tree_old, tree_new, result):
    new, changed, removed, _delta = tree_new.compare_with(tree_old)
    assert (new, changed, removed) == result


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
def test_structured_data_StructuredDataTree_has_edge(tree, edges_t, edges_f):
    for edge_t in edges_t:
        assert tree.has_edge(edge_t)
    for edge_f in edges_f:
        assert not tree.has_edge(edge_f)


@pytest.mark.parametrize("tree,len_children", list(zip(
    trees_old,
    [2, 1, 1, 4, 1, 4],
)))
def test_structured_data_StructuredDataTree_get_children(tree, len_children):
    tree_children = tree.get_children()
    for entry in tree_children:
        assert len(entry) == 3
    assert len(tree_children) == len_children


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataTree_copy(tree):
    copied = tree.copy()
    assert id(tree) != id(copied)
    assert tree.is_equal(copied)


@pytest.mark.parametrize("tree_start,tree_edges", [
    (tree_old_addresses, [
        (tree_old_arrays, ["hardware", "networking"], [
            ("get_sub_attributes", ["hardware", "memory", "arrays", 0]),
            ("get_sub_numeration", ["hardware", "memory", "arrays", 0, "devices"]),
            ("get_sub_numeration", ["hardware", "memory", "arrays", 1, "others"]),
        ]),
        (tree_new_memory, ["hardware", "networking"], [
            ("get_sub_attributes", ["hardware", "memory"]),
        ]),
        (tree_new_interfaces, ["hardware", "networking", "software"], [
            ("get_sub_numeration", ["hardware", "components", "backplanes"]),
            ("get_sub_numeration", ["hardware", "components", "chassis"]),
            ("get_sub_numeration", ["hardware", "components", "containers"]),
            ("get_sub_numeration", ["hardware", "components", "fans"]),
            ("get_sub_numeration", ["hardware", "components", "modules"]),
            ("get_sub_numeration", ["hardware", "components", "others"]),
            ("get_sub_numeration", ["hardware", "components", "psus"]),
            ("get_sub_numeration", ["hardware", "components", "sensors"]),
            ("get_sub_attributes", ["hardware", "system"]),
            ("get_sub_attributes", ["software", "applications", "check_mk", "cluster"]),
            ("get_sub_attributes", ["software", "os"]),
        ])
    ]),
])
def test_structured_data_StructuredDataTree_merge_with_get_sub_children(tree_start, tree_edges):
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


TREE_INV = StructuredDataTree().load_from("%s/tree_inv" % TEST_DIR)
TREE_STATUS = StructuredDataTree().load_from("%s/tree_status" % TEST_DIR)


@pytest.mark.parametrize("tree_inv,tree_status", [
    (TREE_INV, TREE_STATUS),
])
def test_structured_data_StructuredDataTree_merge_with_numeration(tree_inv, tree_status):
    tree_inv.merge_with(tree_status)
    assert 'foobar' in tree_inv.get_raw_tree()
    num = tree_inv.get_sub_numeration(['foobar'])
    assert len(num.get_child_data()) == 5


@pytest.mark.parametrize("tree", trees)
def test_structured_data_StructuredDataTree_get_root_container(tree):
    assert id(tree.get_root_container()) == id(tree._root)


@pytest.mark.parametrize(
    "tree,paths,unavail",
    [
        (
            tree_new_interfaces,
            # container                   numeration                    attributes
            [(["hardware", "components"], None), (["networking", "interfaces"], None),
             (["software", "os"], None)],
            [["hardware", "system"], ["software", "applications"]]),
    ])
def test_structured_data_StructuredDataTree_filtered_tree(tree, paths, unavail):
    filtered = tree.get_filtered_tree(paths)
    assert id(tree) != id(filtered)
    assert not tree.is_equal(filtered)
    for path in unavail:
        assert filtered.get_sub_container(path) is None


@pytest.mark.parametrize("tree,paths,node_types,amount_if_entries", [
    (tree_new_interfaces, [(['networking'], None)], [Container, Attributes], 3178),
    (tree_new_interfaces, [(['networking'], [])], [Attributes], None),
    (tree_new_interfaces, [
        (['networking'], ['total_interfaces', 'total_ethernet_ports', 'available_ethernet_ports'])
    ], [Attributes], None),
    (tree_new_interfaces, [(['networking', 'interfaces'], None)], [Container], 3178),
    (tree_new_interfaces, [(['networking', 'interfaces'], [])], [Container], 3178),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status'])], [Container], 326),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status', 'FOOBAR'])], [Container
                                                                                        ], 326),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status', 'oper_status'])
                          ], [Container], 652),
    (tree_new_interfaces, [(['networking', 'interfaces'], ['admin_status', 'oper_status', 'FOOBAR'])
                          ], [Container], 652),
])
def test_structured_data_StructuredDataTree_filtered_tree_networking(tree, paths, node_types,
                                                                     amount_if_entries):
    filtered = tree.get_filtered_tree(paths)
    assert filtered.has_edge('networking')
    assert not filtered.has_edge('hardware')
    assert not filtered.has_edge('software')

    children = filtered.get_sub_children(['networking'])
    assert len(children) == len(node_types)
    for child in children:
        assert type(child) in node_types  # pylint: disable=unidiomatic-typecheck

    interfaces = filtered.get_sub_numeration(['networking', 'interfaces'])
    if Container in node_types:
        assert bool(interfaces)
        assert interfaces.count_entries() == amount_if_entries
    else:
        assert interfaces is None


def test_structured_data_StructuredDataTree_building_tree():
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

    struct_tree = StructuredDataTree()
    plugin_dict()
    plugin_list()
    plugin_nested_list()
    struct_tree.normalize_nodes()

    assert struct_tree.has_edge("level0_0")
    assert struct_tree.has_edge("level0_1")
    assert struct_tree.has_edge("level0_2")
    assert not struct_tree.has_edge("foobar")

    level1_dict = struct_tree.get_sub_attributes(["level0_0", "level1_dict"])
    level1_list = struct_tree.get_sub_numeration(["level0_1", "level1_list"])
    level1_nested_list_con = struct_tree.get_sub_container(["level0_2", "level1_nested_list"])
    level1_nested_list_num = struct_tree.get_sub_numeration(["level0_2", "level1_nested_list"])
    level1_nested_list_att = struct_tree.get_sub_attributes(["level0_2", "level1_nested_list"])

    assert 'd1' in level1_dict.get_child_data()
    assert 'd2' in level1_dict.get_child_data()
    known_keys = [key for row in level1_list.get_child_data() for key in row]
    assert 'l1' in known_keys
    assert 'l2' in known_keys
    assert level1_nested_list_num is None
    assert level1_nested_list_att is None
    assert list(level1_nested_list_con._edges) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.parametrize("zipped_trees", list(zip(old_trees, new_trees)))
def test_delta_structured_data_tree_serialization(zipped_trees):
    old_tree = StructuredDataTree()
    new_tree = StructuredDataTree()

    old_filename, new_filename = zipped_trees

    old_tree.load_from(old_filename)
    new_tree.load_from(new_filename)
    _, __, ___, delta_tree = old_tree.compare_with(new_tree)

    new_delta_tree = StructuredDataTree()
    new_delta_tree.create_tree_from_raw_tree(delta_tree.get_raw_tree())

    assert delta_tree.is_equal(new_delta_tree)
