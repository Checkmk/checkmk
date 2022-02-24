#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
from typing import List, Union

import pytest

from cmk.utils.structured_data import RetentionIntervals, StructuredDataNode

from cmk.base.agent_based import inventory
from cmk.base.agent_based.inventory._retentions import (
    AttributesUpdater,
    RetentionInfo,
    RetentionsTracker,
    TableUpdater,
)
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow


@pytest.mark.skip("CMK-9861")
def test_aggregator_raises_collision():
    inventory_items: List[Union[Attributes, TableRow]] = [
        Attributes(path=["a", "b", "c"], status_attributes={"foo": "bar"}),
        TableRow(path=["a", "b", "c"], key_columns={"foo": "bar"}),
    ]

    result = inventory.TreeAggregator().aggregate_results(
        inventory_generator=inventory_items,
        retentions_tracker=RetentionsTracker([]),
        raw_cache_info=None,
        is_legacy_plugin=False,
    )

    assert isinstance(result, TypeError)
    assert str(result) == (
        "Cannot create TableRow at path ['a', 'b', 'c']: this is a Attributes node."
    )


_TREE_WITH_OTHER = StructuredDataNode()
_TREE_WITH_OTHER.setdefault_node(["other"])
_TREE_WITH_EDGE = StructuredDataNode()
_TREE_WITH_EDGE.setdefault_node(["edge"])


@pytest.mark.parametrize(
    "old_tree, inv_tree",
    [
        (_TREE_WITH_OTHER, None),
        (_TREE_WITH_EDGE, None),
        (_TREE_WITH_EDGE, _TREE_WITH_OTHER),
        (_TREE_WITH_OTHER, _TREE_WITH_EDGE),
    ],
)
def test__tree_nodes_are_not_equal(old_tree, inv_tree):
    assert inventory._tree_nodes_are_equal(old_tree, inv_tree, "edge") is False


@pytest.mark.parametrize(
    "old_tree, inv_tree",
    [
        (_TREE_WITH_OTHER, _TREE_WITH_OTHER),
        (_TREE_WITH_EDGE, _TREE_WITH_EDGE),
    ],
)
def test__tree_nodes_are_equal(old_tree, inv_tree):
    assert inventory._tree_nodes_are_equal(old_tree, inv_tree, "edge") is True


def test_integrate_attributes():
    inventory_items: List[Attributes] = [
        Attributes(
            path=["a", "b", "c"],
            inventory_attributes={
                "foo0": "bar0",
                "foo1": "bar1",
            },
        ),
    ]

    tree_aggr = inventory.TreeAggregator()
    tree_aggr.aggregate_results(
        inventory_generator=inventory_items,
        retentions_tracker=RetentionsTracker([]),
        raw_cache_info=None,
        is_legacy_plugin=False,
    )

    assert tree_aggr.trees.inventory.serialize() == {
        "Attributes": {},
        "Nodes": {
            "a": {
                "Attributes": {},
                "Nodes": {
                    "b": {
                        "Attributes": {},
                        "Nodes": {
                            "c": {
                                "Attributes": {
                                    "Pairs": {"foo0": "bar0", "foo1": "bar1"},
                                },
                                "Nodes": {},
                                "Table": {},
                            }
                        },
                        "Table": {},
                    }
                },
                "Table": {},
            }
        },
        "Table": {},
    }


def test_integrate_table_row():
    inventory_items: List[TableRow] = [
        TableRow(
            path=["a", "b", "c"],
            key_columns={"foo": "baz"},
            inventory_columns={
                "col1": "baz val1",
                "col2": "baz val2",
                "col3": "baz val3",
            },
        ),
        TableRow(
            path=["a", "b", "c"],
            key_columns={"foo": "bar"},
            inventory_columns={
                "col1": "bar val1",
                "col2": "bar val2",
            },
        ),
        TableRow(
            path=["a", "b", "c"],
            key_columns={"foo": "bar"},
            inventory_columns={
                "col1": "new bar val1",
                "col3": "bar val3",
            },
        ),
    ]

    tree_aggr = inventory.TreeAggregator()
    tree_aggr.aggregate_results(
        inventory_generator=inventory_items,
        retentions_tracker=RetentionsTracker([]),
        raw_cache_info=None,
        is_legacy_plugin=False,
    )

    assert tree_aggr.trees.inventory.serialize() == {
        "Attributes": {},
        "Nodes": {
            "a": {
                "Attributes": {},
                "Nodes": {
                    "b": {
                        "Attributes": {},
                        "Nodes": {
                            "c": {
                                "Attributes": {},
                                "Nodes": {},
                                "Table": {
                                    "KeyColumns": ["foo"],
                                    "Rows": [
                                        {
                                            "col1": "baz " "val1",
                                            "col2": "baz " "val2",
                                            "col3": "baz " "val3",
                                            "foo": "baz",
                                        },
                                        {
                                            "col1": "new " "bar " "val1",
                                            "col2": "bar " "val2",
                                            "col3": "bar " "val3",
                                            "foo": "bar",
                                        },
                                    ],
                                },
                            }
                        },
                        "Table": {},
                    }
                },
                "Table": {},
            }
        },
        "Table": {},
    }


@pytest.mark.parametrize(
    "raw_intervals, node_name, path, raw_cache_info",
    [
        # === Attributes ===
        # empty config
        ([], "", [], None),
        ([], "Attributes", [], None),
        ([], "Attributes", ["path-to", "node"], None),
        ([], "Attributes", ["path-to", "node"], (1, 2)),
        # config, wrong path
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "Attributes",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "Attributes",
            ["path-to", "node"],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "Attributes",
            ["path-to", "node"],
            (1, 2),
        ),
        # config, right path, no choices
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "Attributes",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "Attributes",
            ["path-to", "node"],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "Attributes",
            ["path-to", "node"],
            (1, 2),
        ),
        # config, right path, all attributes
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": "all",
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": "all",
                }
            ],
            "Attributes",
            [],
            None,
        ),
        # config, right path, attributes choices
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": ("choices", ["some", "keys"]),
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": ("choices", ["some", "keys"]),
                }
            ],
            "Attributes",
            [],
            None,
        ),
        # === Table ===
        # empty config
        ([], "", [], None),
        ([], "Table", [], None),
        ([], "Table", ["path-to", "node"], None),
        ([], "Table", ["path-to", "node"], (1, 2)),
        # config, wrong path
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "Table",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "Table",
            ["path-to", "node"],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "Table",
            ["path-to", "node"],
            (1, 2),
        ),
        # config, right path, no choices
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "Table",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "Table",
            ["path-to", "node"],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                }
            ],
            "Table",
            ["path-to", "node"],
            (1, 2),
        ),
        # config, right path, all columns
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": "all",
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": "all",
                }
            ],
            "Table",
            [],
            None,
        ),
        # config, right path, columns choices
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": ("choices", ["some", "keys"]),
                }
            ],
            "",
            [],
            None,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": ("choices", ["some", "keys"]),
                }
            ],
            "Table",
            [],
            None,
        ),
    ],
)
def test_retentions_add_cache_info_no_match(
    raw_intervals,
    node_name,
    path,
    raw_cache_info,
):
    now = 100
    retentions_tracker = RetentionsTracker(raw_intervals)
    retentions_tracker.may_add_cache_info(
        now=now,
        node_name=node_name,
        path=path,
        raw_cache_info=raw_cache_info,
    )
    assert retentions_tracker.retention_infos == {}


@pytest.mark.parametrize(
    "raw_intervals, node_name, path, raw_cache_info, expected_intervals, match_some_keys, match_other_keys",
    [
        # === Attributes ===
        # config, right path, all attributes
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": "all",
                }
            ],
            "Attributes",
            ["path-to", "node"],
            None,
            RetentionIntervals(
                cached_at=100,
                cache_interval=0,
                retention_interval=3,
            ),
            True,
            True,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": "all",
                }
            ],
            "Attributes",
            ["path-to", "node"],
            (1, 2),
            RetentionIntervals(
                cached_at=1,
                cache_interval=2,
                retention_interval=3,
            ),
            True,
            True,
        ),
        # config, right path, attributes choices
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": ("choices", ["some", "keys"]),
                }
            ],
            "Attributes",
            ["path-to", "node"],
            None,
            RetentionIntervals(
                cached_at=100,
                cache_interval=0,
                retention_interval=3,
            ),
            True,
            False,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "attributes": ("choices", ["some", "keys"]),
                }
            ],
            "Attributes",
            ["path-to", "node"],
            (1, 2),
            RetentionIntervals(
                cached_at=1,
                cache_interval=2,
                retention_interval=3,
            ),
            True,
            False,
        ),
        # === Table ===
        # config, right path, all columns
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": "all",
                }
            ],
            "Table",
            ["path-to", "node"],
            None,
            RetentionIntervals(
                cached_at=100,
                cache_interval=0,
                retention_interval=3,
            ),
            True,
            True,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": "all",
                }
            ],
            "Table",
            ["path-to", "node"],
            (1, 2),
            RetentionIntervals(
                cached_at=1,
                cache_interval=2,
                retention_interval=3,
            ),
            True,
            True,
        ),
        # config, right path, columns choices
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": ("choices", ["some", "keys"]),
                }
            ],
            "Table",
            ["path-to", "node"],
            None,
            RetentionIntervals(
                cached_at=100,
                cache_interval=0,
                retention_interval=3,
            ),
            True,
            False,
        ),
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.node",
                    "columns": ("choices", ["some", "keys"]),
                }
            ],
            "Table",
            ["path-to", "node"],
            (1, 2),
            RetentionIntervals(
                cached_at=1,
                cache_interval=2,
                retention_interval=3,
            ),
            True,
            False,
        ),
    ],
)
def test_retentions_add_cache_info(
    raw_intervals,
    node_name,
    path,
    raw_cache_info,
    expected_intervals,
    match_some_keys,
    match_other_keys,
):
    now = 100
    retentions_tracker = RetentionsTracker(raw_intervals)
    retentions_tracker.may_add_cache_info(
        now=now,
        node_name=node_name,
        path=path,
        raw_cache_info=raw_cache_info,
    )

    retention_info = retentions_tracker.retention_infos.get((("path-to", "node"), node_name))
    assert retention_info is not None

    assert retention_info.intervals == expected_intervals

    for key in ["some", "keys"]:
        assert retention_info.filter_func(key) is match_some_keys

    for key in ["other", "keyz"]:
        assert retention_info.filter_func(key) is match_other_keys


def _make_trees(previous_attributes_retentions, previous_table_retentions):
    previous_tree = StructuredDataNode.deserialize(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "path-to": {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "node": {
                            "Attributes": {
                                "Pairs": {"old": "Key", "keys": "Previous Keys"},
                                "Retentions": previous_attributes_retentions,
                            },
                            "Table": {
                                "KeyColumns": ["ident"],
                                "Rows": [
                                    {"ident": "Ident 1", "old": "Key 1", "keys": "Previous Keys 1"},
                                    {"ident": "Ident 2", "old": "Key 2", "keys": "Previous Keys 2"},
                                ],
                                "Retentions": previous_table_retentions,
                            },
                            "Nodes": {},
                        }
                    },
                }
            },
        }
    )
    inv_tree = StructuredDataNode.deserialize(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "path-to": {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "node": {
                            "Attributes": {
                                "Pairs": {"new": "Key", "keys": "New Keys"},
                            },
                            "Table": {
                                "KeyColumns": ["ident"],
                                "Rows": [
                                    {"ident": "Ident 1", "new": "Key 1", "keys": "New Keys 1"},
                                    {"ident": "Ident 2", "new": "Key 2", "keys": "New Keys 2"},
                                ],
                            },
                            "Nodes": {},
                        }
                    },
                }
            },
        }
    )
    return previous_tree, inv_tree


#   ---no previous node, no inv node----------------------------------------


def test_updater_null_obj_attributes():
    inv_tree = StructuredDataNode()
    updater = AttributesUpdater(
        RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree,
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(-1)
    assert not result.save_tree
    assert not result.reason

    assert inv_tree.get_node(["path-to", "node"]) is None


def test_updater_null_obj_attributes_outdated():
    inv_tree = StructuredDataNode()
    updater = AttributesUpdater(
        RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree,
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(1000)
    assert not result.save_tree
    assert not result.reason

    assert inv_tree.get_node(["path-to", "node"]) is None


def test_updater_null_obj_tables():
    inv_tree = StructuredDataNode()
    updater = TableUpdater(
        RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree,
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(-1)
    assert not result.save_tree
    assert not result.reason

    assert inv_tree.get_node(["path-to", "node"]) is None


def test_updater_null_obj_tables_outdated():
    inv_tree = StructuredDataNode()
    updater = TableUpdater(
        RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree,
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(1000)
    assert not result.save_tree
    assert not result.reason

    assert inv_tree.get_node(["path-to", "node"]) is None


#   ---no previous node, inv node-------------------------------------------


@pytest.mark.parametrize(
    "filter_func, path, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], ["path-to", "node"], {}),
        (
            lambda key: key in ["new", "keyz"],
            ["path-to", "node"],
            {"new": RetentionIntervals(1, 2, 3)},
        ),
    ],
)
def test_updater_handle_inv_attributes(
    filter_func,
    path,
    expected_retentions,
):
    _previous_tree, inv_tree = _make_trees({}, {})

    updater = AttributesUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree.get_node(path),
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(-1)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, path, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], ["path-to", "node"], {}),
        (
            lambda key: key in ["new", "keyz"],
            ["path-to", "node"],
            {"new": RetentionIntervals(1, 2, 3)},
        ),
    ],
)
def test_updater_handle_inv_attributes_outdated(
    filter_func,
    path,
    expected_retentions,
):
    _previous_tree, inv_tree = _make_trees({}, {})

    updater = AttributesUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree.get_node(path),
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(1000)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, path, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], ["path-to", "node"], {}),
        (
            lambda key: key in ["new", "keyz"],
            ["path-to", "node"],
            {
                ("Ident 1",): {"new": RetentionIntervals(1, 2, 3)},
                ("Ident 2",): {"new": RetentionIntervals(1, 2, 3)},
            },
        ),
    ],
)
def test_updater_handle_inv_tables(
    filter_func,
    path,
    expected_retentions,
):
    _previous_tree, inv_tree = _make_trees({}, {})

    updater = TableUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree.get_node(path),
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(-1)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.table.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, path, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], ["path-to", "node"], {}),
        (
            lambda key: key in ["new", "keyz"],
            ["path-to", "node"],
            {
                ("Ident 1",): {"new": RetentionIntervals(1, 2, 3)},
                ("Ident 2",): {"new": RetentionIntervals(1, 2, 3)},
            },
        ),
    ],
)
def test_updater_handle_inv_tables_outdated(
    filter_func,
    path,
    expected_retentions,
):
    _previous_tree, inv_tree = _make_trees({}, {})

    updater = TableUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
        inv_tree.get_node(path),
        StructuredDataNode(),
    )
    result = updater.filter_and_merge(1000)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.table.retentions == expected_retentions


#   ---previous node, new inv node------------------------------------------


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (lambda key: key in ["old", "keyz"], {"old": RetentionIntervals(1, 2, 3)}),
    ],
)
def test_updater_merge_previous_attributes(
    filter_func,
    expected_retentions,
):
    previous_tree, _inv_tree = _make_trees({"old": (1, 2, 3)}, {})
    inv_tree = StructuredDataNode()

    updater = AttributesUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
        inv_tree.setdefault_node(["path-to", "node"]),
        previous_tree.get_node(["path-to", "node"]),
    )
    result = updater.filter_and_merge(-1)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.attributes.retentions == expected_retentions

    if expected_retentions:
        assert "old" in inv_node.attributes.pairs


@pytest.mark.parametrize(
    "filter_func",
    [
        lambda key: key in ["unknown", "keyz"],
        lambda key: key in ["old", "keyz"],
    ],
)
def test_updater_merge_previous_attributes_outdated(filter_func):
    previous_tree, _inv_tree = _make_trees({"old": (1, 2, 3)}, {})
    inv_tree = StructuredDataNode()

    updater = AttributesUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
        inv_tree.setdefault_node(["path-to", "node"]),
        previous_tree.get_node(["path-to", "node"]),
    )
    result = updater.filter_and_merge(1000)
    assert not result.save_tree
    assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.attributes.retentions == {}


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key in ["old", "keyz"],
            {
                ("Ident 1",): {"old": RetentionIntervals(1, 2, 3)},
                ("Ident 2",): {"old": RetentionIntervals(1, 2, 3)},
            },
        ),
    ],
)
def test_updater_merge_previous_tables(
    filter_func,
    expected_retentions,
):
    previous_tree, _inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {"old": (1, 2, 3)},
            ("Ident 2",): {"old": RetentionIntervals(1, 2, 3)},
        },
    )
    inv_tree = StructuredDataNode()

    updater = TableUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
        inv_tree.setdefault_node(["path-to", "node"]),
        previous_tree.get_node(["path-to", "node"]),
    )
    result = updater.filter_and_merge(-1)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.table.retentions == expected_retentions

    if expected_retentions:
        for row in inv_node.table.rows:
            assert "old" in row


@pytest.mark.parametrize(
    "filter_func",
    [
        lambda key: key in ["unknown", "keyz"],
        lambda key: key in ["old", "keyz"],
    ],
)
def test_updater_merge_previous_tables_outdated(filter_func):
    previous_tree, _inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {"old": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3)},
        },
    )
    inv_tree = StructuredDataNode()

    updater = TableUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
        inv_tree.setdefault_node(["path-to", "node"]),
        previous_tree.get_node(["path-to", "node"]),
    )
    result = updater.filter_and_merge(1000)
    assert not result.save_tree
    assert not result.reason

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None
    assert inv_node.table.retentions == {}


#   ---previous node, inv node----------------------------------------------


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key
            in [
                "old",
                "and",
                "new",
                "keys",
            ],
            {
                "old": RetentionIntervals(1, 2, 3),
                "new": RetentionIntervals(4, 5, 6),
                "keys": RetentionIntervals(4, 5, 6),
            },
        ),
    ],
)
def test_updater_merge_attributes(
    filter_func,
    expected_retentions,
):
    previous_tree, inv_tree = _make_trees(
        {
            "old": (1, 2, 3),
            "keys": (1, 2, 3),
        },
        {},
    )

    previous_node = previous_tree.get_node(["path-to", "node"])
    assert previous_node is not None

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None

    updater = AttributesUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
        inv_node,
        previous_node,
    )
    result = updater.filter_and_merge(-1)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    assert inv_node.attributes.retentions == expected_retentions

    if expected_retentions:
        assert "old" in inv_node.attributes.pairs
        assert inv_node.attributes.pairs.get("keys") == "New Keys"


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key
            in [
                "old",
                "and",
                "new",
                "keys",
            ],
            {
                "new": RetentionIntervals(4, 5, 6),
                "keys": RetentionIntervals(4, 5, 6),
            },
        ),
    ],
)
def test_updater_merge_attributes_outdated(
    filter_func,
    expected_retentions,
):
    previous_tree, inv_tree = _make_trees(
        {
            "old": (1, 2, 3),
            "keys": (1, 2, 3),
        },
        {},
    )

    previous_node = previous_tree.get_node(["path-to", "node"])
    assert previous_node is not None

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None

    updater = AttributesUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
        inv_node,
        previous_node,
    )
    result = updater.filter_and_merge(1000)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key
            in [
                "old",
                "and",
                "new",
                "keys",
            ],
            {
                ("Ident 1",): {
                    "old": RetentionIntervals(1, 2, 3),
                    "new": RetentionIntervals(4, 5, 6),
                    "keys": RetentionIntervals(4, 5, 6),
                },
                ("Ident 2",): {
                    "old": RetentionIntervals(1, 2, 3),
                    "new": RetentionIntervals(4, 5, 6),
                    "keys": RetentionIntervals(4, 5, 6),
                },
            },
        ),
    ],
)
def test_updater_merge_tables(filter_func, expected_retentions):
    previous_tree, inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {
                "old": (1, 2, 3),
                "keys": (1, 2, 3),
            },
            ("Ident 2",): {
                "old": (1, 2, 3),
                "keys": (1, 2, 3),
            },
        },
    )

    previous_node = previous_tree.get_node(["path-to", "node"])
    assert previous_node is not None

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None

    updater = TableUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
        inv_node,
        previous_node,
    )
    result = updater.filter_and_merge(-1)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    assert inv_node.table.retentions == expected_retentions

    if expected_retentions:
        for row in inv_node.table.rows:
            assert "old" in row
            assert row.get("keys").startswith("New Keys")


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key
            in [
                "old",
                "and",
                "new",
                "keys",
            ],
            {
                ("Ident 1",): {
                    "new": RetentionIntervals(4, 5, 6),
                    "keys": RetentionIntervals(4, 5, 6),
                },
                ("Ident 2",): {
                    "new": RetentionIntervals(4, 5, 6),
                    "keys": RetentionIntervals(4, 5, 6),
                },
            },
        ),
    ],
)
def test_updater_merge_tables_outdated(
    filter_func,
    expected_retentions,
):
    previous_tree, inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {"old": (1, 2, 3), "keys": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3), "keys": (1, 2, 3)},
        },
    )

    previous_node = previous_tree.get_node(["path-to", "node"])
    assert previous_node is not None

    inv_node = inv_tree.get_node(["path-to", "node"])
    assert inv_node is not None

    updater = TableUpdater(
        RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
        inv_node,
        previous_node,
    )
    result = updater.filter_and_merge(1000)
    if expected_retentions:
        assert result.save_tree
        assert result.reason
    else:
        assert not result.save_tree
        assert not result.reason

    assert inv_node.table.retentions == expected_retentions
