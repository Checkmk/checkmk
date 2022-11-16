#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest

from tests.testlib.base import Scenario

import cmk.utils.debug
from cmk.utils.structured_data import (
    ATTRIBUTES_KEY,
    RetentionIntervals,
    SDFilterFunc,
    SDPath,
    StructuredDataNode,
    TABLE_KEY,
    UpdateResult,
)
from cmk.utils.type_defs import EVERYTHING

from cmk.core_helpers.type_defs import NO_SELECTION

import cmk.base.agent_based.inventory._inventory as _inventory
import cmk.base.config as config
from cmk.base.agent_based.data_provider import ParsedSectionsBroker
from cmk.base.agent_based.inventory._inventory import (
    _inventorize_real_host,
    _parse_inventory_plugin_item,
    InventoryTrees,
)
from cmk.base.agent_based.inventory._tree_aggregator import (
    ItemsOfInventoryPlugin,
    RealHostTreeUpdater,
    RetentionInfo,
)
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow
from cmk.base.config import HostConfig


@pytest.mark.parametrize(
    "item, known_class_name",
    [
        (Attributes(path=["a", "b", "c"], status_attributes={"foo": "bar"}), "TableRow"),
        (TableRow(path=["a", "b", "c"], key_columns={"foo": "bar"}), "Attributes"),
    ],
)
def test_item_collisions(item: Attributes | TableRow, known_class_name: str) -> None:
    # For some reason, the callee raises instead of returning the exception if
    # it runs in debug mode.  So let us explicitly disable that here.
    cmk.utils.debug.disable()

    with pytest.raises(TypeError) as e:
        _parse_inventory_plugin_item(item, known_class_name)

        assert str(e) == (
            "Cannot create TableRow at path ['a', 'b', 'c']: this is a Attributes node."
        )


_TREE_WITH_OTHER = StructuredDataNode()
_TREE_WITH_OTHER.setdefault_node(("other",))
_TREE_WITH_EDGE = StructuredDataNode()
_TREE_WITH_EDGE.setdefault_node(("edge",))


@pytest.mark.parametrize(
    "old_tree, inv_tree",
    [
        (_TREE_WITH_EDGE, _TREE_WITH_OTHER),
        (_TREE_WITH_OTHER, _TREE_WITH_EDGE),
    ],
)
def test__tree_nodes_are_not_equal(
    old_tree: StructuredDataNode,
    inv_tree: StructuredDataNode,
) -> None:
    assert _inventory._tree_nodes_are_equal(old_tree, inv_tree, "edge") is False


@pytest.mark.parametrize(
    "old_tree, inv_tree",
    [
        (_TREE_WITH_OTHER, _TREE_WITH_OTHER),
        (_TREE_WITH_EDGE, _TREE_WITH_EDGE),
    ],
)
def test__tree_nodes_are_equal(old_tree: StructuredDataNode, inv_tree: StructuredDataNode) -> None:
    assert _inventory._tree_nodes_are_equal(old_tree, inv_tree, "edge") is True


def test__inventorize_real_host_only_items() -> None:
    trees, update_result = _inventorize_real_host(
        now=0,
        items_of_inventory_plugins=[
            ItemsOfInventoryPlugin(
                items=[
                    Attributes(
                        path=["path-to", "node-with-attrs"],
                        inventory_attributes={
                            "foo0": "bar0",
                            "foo1": "bar1",
                        },
                    ),
                    Attributes(
                        path=["path-to", "node-with-attrs"],
                        inventory_attributes={
                            "foo1": "2. bar1",
                            "foo2": "bar2",
                        },
                    ),
                    TableRow(
                        path=["path-to", "node-with-table"],
                        key_columns={"foo": "bar0"},
                        inventory_columns={
                            "col0": "bar0 val0",
                            "col1": "bar0 val1",
                        },
                    ),
                    TableRow(
                        path=["path-to", "node-with-table"],
                        key_columns={"foo": "bar1"},
                        inventory_columns={
                            "col0": "bar1 val0",
                            "col1": "bar1 val1",
                        },
                    ),
                    TableRow(
                        path=["path-to", "node-with-table"],
                        key_columns={"foo": "bar0"},
                        inventory_columns={
                            "col1": "2. bar0 val1",
                        },
                    ),
                ],
                raw_cache_info=None,
            )
        ],
        raw_intervals_from_config=[],
        old_tree=StructuredDataNode(),
    )

    assert trees.inventory.serialize() == {
        "Attributes": {},
        "Nodes": {
            "path-to": {
                "Attributes": {},
                "Nodes": {
                    "node-with-attrs": {
                        "Attributes": {
                            "Pairs": {
                                "foo0": "bar0",
                                "foo1": "2. bar1",
                                "foo2": "bar2",
                            },
                        },
                        "Nodes": {},
                        "Table": {},
                    },
                    "node-with-table": {
                        "Attributes": {},
                        "Nodes": {},
                        "Table": {
                            "KeyColumns": ["foo"],
                            "Rows": [
                                {
                                    "foo": "bar0",
                                    "col0": "bar0 val0",
                                    "col1": "2. bar0 val1",
                                },
                                {
                                    "foo": "bar1",
                                    "col0": "bar1 val0",
                                    "col1": "bar1 val1",
                                },
                            ],
                        },
                    },
                },
                "Table": {},
            },
            "software": {
                "Attributes": {},
                "Nodes": {
                    "applications": {
                        "Attributes": {},
                        "Nodes": {
                            "check_mk": {
                                "Attributes": {},
                                "Nodes": {
                                    "cluster": {
                                        "Attributes": {"Pairs": {"is_cluster": False}},
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
            },
        },
        "Table": {},
    }
    assert not update_result.save_tree
    assert update_result.reason == "No retention intervals found."


@pytest.mark.parametrize(
    "raw_intervals, node_type, path, raw_cache_info",
    [
        # === Attributes ===
        # empty config
        ([], "", tuple(), None),
        ([], "Attributes", tuple(), None),
        ([], "Attributes", ("path-to", "node"), None),
        ([], "Attributes", ("path-to", "node"), (1, 2)),
        # config, wrong path
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "",
            tuple(),
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
            tuple(),
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
            ("path-to", "node"),
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
            ("path-to", "node"),
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
            tuple(),
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
            tuple(),
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
            ("path-to", "node"),
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
            ("path-to", "node"),
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
            tuple(),
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
            tuple(),
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
            tuple(),
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
            tuple(),
            None,
        ),
        # === Table ===
        # empty config
        ([], "", tuple(), None),
        ([], "Table", tuple(), None),
        ([], "Table", ("path-to", "node"), None),
        ([], "Table", ("path-to", "node"), (1, 2)),
        # config, wrong path
        (
            [
                {
                    "interval": 3,
                    "visible_raw_path": "path-to.foo",
                }
            ],
            "",
            tuple(),
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
            tuple(),
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
            ("path-to", "node"),
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
            ("path-to", "node"),
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
            tuple(),
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
            tuple(),
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
            ("path-to", "node"),
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
            ("path-to", "node"),
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
            tuple(),
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
            tuple(),
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
            tuple(),
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
            tuple(),
            None,
        ),
    ],
)
def test_retentions_add_cache_info_no_match(
    raw_intervals: list[dict],
    node_type: str,
    path: SDPath,
    raw_cache_info: tuple[int, int] | None,
) -> None:
    items: list[Attributes | TableRow]
    if node_type == ATTRIBUTES_KEY:
        items = [
            Attributes(
                path=["path-to", "node"] if path else ["unknown-to", "node"],
                inventory_attributes={},
                status_attributes={},
            ),
        ]
    elif node_type == TABLE_KEY:
        items = [
            TableRow(
                path=["path-to", "node"] if path else ["unknown-to", "node"],
                key_columns={"foo": "Foo"},
                inventory_columns={},
                status_columns={},
            ),
        ]
    else:
        items = []

    now = 100
    tree_updater = RealHostTreeUpdater(raw_intervals)
    tree_updater.may_add_cache_info(
        now=now,
        items_of_inventory_plugins=[
            ItemsOfInventoryPlugin(
                items=items,
                raw_cache_info=raw_cache_info,
            ),
        ],
    )
    assert tree_updater._retention_infos == {}


@pytest.mark.parametrize(
    "raw_intervals, node_type, raw_cache_info, expected_intervals, match_some_keys, match_other_keys",
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
    raw_intervals: list[dict],
    node_type: str,
    raw_cache_info: tuple[int, int] | None,
    expected_intervals: RetentionIntervals,
    match_some_keys: bool,
    match_other_keys: bool,
) -> None:
    items: list[Attributes | TableRow]
    if node_type == ATTRIBUTES_KEY:
        items = [
            Attributes(
                path=["path-to", "node"],
                inventory_attributes={},
                status_attributes={},
            ),
        ]
    elif node_type == TABLE_KEY:
        items = [
            TableRow(
                path=["path-to", "node"],
                key_columns={"foo": "Foo"},
                inventory_columns={},
                status_columns={},
            ),
        ]
    else:
        items = []

    now = 100
    tree_updater = RealHostTreeUpdater(raw_intervals)
    tree_updater.may_add_cache_info(
        now=now,
        items_of_inventory_plugins=[
            ItemsOfInventoryPlugin(
                items=items,
                raw_cache_info=raw_cache_info,
            ),
        ],
    )

    retention_info = tree_updater._retention_infos.get((("path-to", "node"), node_type))
    assert retention_info is not None

    assert retention_info.intervals == expected_intervals

    for key in ["some", "keys"]:
        assert retention_info.filter_func(key) is match_some_keys

    for key in ["other", "keyz"]:
        assert retention_info.filter_func(key) is match_other_keys


def _make_trees(
    previous_attributes_retentions: dict, previous_table_retentions: dict
) -> tuple[StructuredDataNode, StructuredDataNode]:
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


def test_updater_null_obj_attributes() -> None:
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    assert not update_result.save_tree
    assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.is_empty()


def test_updater_null_obj_attributes_outdated() -> None:
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    assert not update_result.save_tree
    assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.is_empty()


def test_updater_null_obj_tables() -> None:
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    assert not update_result.save_tree
    assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.is_empty()


def test_updater_null_obj_tables_outdated() -> None:
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            lambda key: True,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    assert not update_result.save_tree
    assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.is_empty()


#   ---no previous node, inv node-------------------------------------------


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (
            lambda key: key in ["unknown", "keyz"],
            {},
        ),
        (
            lambda key: key in ["new", "keyz"],
            {"new": RetentionIntervals(1, 2, 3)},
        ),
    ],
)
def test_updater_handle_inv_attributes(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    _previous_tree, inv_tree = _make_trees({}, {})

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    fst_inv_node = inv_tree.get_node(("path-to", "node"))
    assert isinstance(fst_inv_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (
            lambda key: key in ["unknown", "keyz"],
            {},
        ),
        (
            lambda key: key in ["new", "keyz"],
            {"new": RetentionIntervals(1, 2, 3)},
        ),
    ],
)
def test_updater_handle_inv_attributes_outdated(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    _previous_tree, inv_tree = _make_trees({}, {})

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    fst_inv_node = inv_tree.get_node(("path-to", "node"))
    assert isinstance(fst_inv_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (
            lambda key: key in ["unknown", "keyz"],
            {},
        ),
        (
            lambda key: key in ["new", "keyz"],
            {
                ("Ident 1",): {"new": RetentionIntervals(1, 2, 3)},
                ("Ident 2",): {"new": RetentionIntervals(1, 2, 3)},
            },
        ),
    ],
)
def test_updater_handle_inv_tables(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    _previous_tree, inv_tree = _make_trees({}, {})

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    fst_inv_node = inv_tree.get_node(("path-to", "node"))
    assert isinstance(fst_inv_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.table.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (
            lambda key: key in ["unknown", "keyz"],
            {},
        ),
        (
            lambda key: key in ["new", "keyz"],
            {
                ("Ident 1",): {"new": RetentionIntervals(1, 2, 3)},
                ("Ident 2",): {"new": RetentionIntervals(1, 2, 3)},
            },
        ),
    ],
)
def test_updater_handle_inv_tables_outdated(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    _previous_tree, inv_tree = _make_trees({}, {})

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            filter_func,
            RetentionIntervals(1, 2, 3),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=StructuredDataNode(),
    )

    fst_inv_node = inv_tree.get_node(("path-to", "node"))
    assert isinstance(fst_inv_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
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
def test_updater_merge_previous_attributes(  # type:ignore[no-untyped-def]
    filter_func: SDFilterFunc,
    expected_retentions: dict,
):
    previous_tree, _inv_tree = _make_trees({"old": (1, 2, 3)}, {})
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": -3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert isinstance(previous_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
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
def test_updater_merge_previous_attributes_outdated(filter_func: SDFilterFunc) -> None:
    previous_tree, _inv_tree = _make_trees({"old": (1, 2, 3)}, {})
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": -3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert isinstance(previous_node, StructuredDataNode)

    assert not update_result.save_tree
    assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
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
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    previous_tree, _inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {"old": (1, 2, 3)},
            ("Ident 2",): {"old": RetentionIntervals(1, 2, 3)},
        },
    )
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": -3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert isinstance(previous_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
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
def test_updater_merge_previous_tables_outdated(filter_func: SDFilterFunc) -> None:
    previous_tree, _inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {"old": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3)},
        },
    )
    inv_tree = StructuredDataNode()

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": -3,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            filter_func,
            RetentionIntervals(-1, -2, -3),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert isinstance(previous_node, StructuredDataNode)

    assert not update_result.save_tree
    assert not update_result.reason

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None
    assert inv_node.table.retentions == {}


#   ---previous node, inv node----------------------------------------------


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key in ["old", "and", "new", "keys"],
            {
                "old": RetentionIntervals(1, 2, 3),
                "new": RetentionIntervals(4, 5, 6),
                "keys": RetentionIntervals(4, 5, 6),
            },
        ),
    ],
)
def test_updater_merge_attributes(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    previous_tree, inv_tree = _make_trees(
        {
            "old": (1, 2, 3),
            "keys": (1, 2, 3),
        },
        {},
    )

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 6,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    assert inv_node.attributes.retentions == expected_retentions

    if expected_retentions:
        assert "old" in inv_node.attributes.pairs
        assert inv_node.attributes.pairs.get("keys") == "New Keys"


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (lambda key: key in ["unknown", "keyz"], {}),
        (
            lambda key: key in ["old", "and", "new", "keys"],
            {
                "new": RetentionIntervals(4, 5, 6),
                "keys": RetentionIntervals(4, 5, 6),
            },
        ),
    ],
)
def test_updater_merge_attributes_outdated(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    previous_tree, inv_tree = _make_trees(
        {
            "old": (1, 2, 3),
            "keys": (1, 2, 3),
        },
        {},
    )

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 6,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Attributes"): RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (
            lambda key: key in ["unknown", "keyz"],
            {},
        ),
        (
            lambda key: key in ["old", "and", "new", "keys"],
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
def test_updater_merge_tables(
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
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

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 6,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
    }
    update_result = tree_updater.may_update(
        now=-1,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    assert inv_node.table.retentions == expected_retentions

    if expected_retentions:
        for row in inv_node.table.rows:
            assert "old" in row
            assert row["keys"].startswith("New Keys")


@pytest.mark.parametrize(
    "filter_func, expected_retentions",
    [
        (
            lambda key: key in ["unknown", "keyz"],
            {},
        ),
        (
            lambda key: key in ["old", "and", "new", "keys"],
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
    filter_func: SDFilterFunc,
    expected_retentions: dict,
) -> None:
    previous_tree, inv_tree = _make_trees(
        {},
        {
            ("Ident 1",): {"old": (1, 2, 3), "keys": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3), "keys": (1, 2, 3)},
        },
    )

    tree_updater = RealHostTreeUpdater(
        [
            {
                "interval": 6,
                "visible_raw_path": "path-to.node",
                "columns": "foo",  # Value is not important here
            }
        ],
    )
    tree_updater._retention_infos = {
        (("path-to", "node"), "Table"): RetentionInfo(
            filter_func,
            RetentionIntervals(4, 5, 6),
        ),
    }
    update_result = tree_updater.may_update(
        now=1000,
        inventory_tree=inv_tree,
        previous_tree=previous_tree,
    )

    previous_node = previous_tree.get_node(("path-to", "node"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reason
    else:
        assert not update_result.save_tree
        assert not update_result.reason

    assert inv_node.table.retentions == expected_retentions


@pytest.mark.parametrize(
    "failed_state, expected",
    [
        (None, 1),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
    ],
)
def test_check_inventory_tree(
    monkeypatch: pytest.MonkeyPatch,
    failed_state: int | None,
    expected: int,
) -> None:
    hostname = "my-host"
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    monkeypatch.setattr(
        _inventory,
        "_fetch_real_host_data",
        lambda *args, **kw: _inventory.FetchedDataResult(
            parsed_sections_broker=ParsedSectionsBroker({}),
            source_results=[],
            parsing_errors=[],
            processing_failed=True,
            no_data_or_files=False,
        ),
    )

    monkeypatch.setattr(
        _inventory,
        "_inventorize_real_host",
        lambda *args, **kw: (
            InventoryTrees(
                inventory=StructuredDataNode(),
                status_data=StructuredDataNode(),
            ),
            UpdateResult(save_tree=False, reason=""),
        ),
    )

    check_result = _inventory.check_inventory_tree(
        hostname,
        host_config=HostConfig.make_host_config(hostname),
        selected_sections=NO_SELECTION,
        run_plugin_names=EVERYTHING,
        parameters=config.HWSWInventoryParameters.from_raw(
            {} if failed_state is None else {"inv-fail-status": failed_state}
        ),
        old_tree=StructuredDataNode(),
    ).check_result

    assert expected == check_result.state
    assert "Cannot update tree" in check_result.summary


@pytest.mark.parametrize("processing_failed", [True, False])
def test_check_inventory_tree_no_data_or_files(
    monkeypatch: pytest.MonkeyPatch,
    processing_failed: bool,
) -> None:
    hostname = "my-host"
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    monkeypatch.setattr(
        _inventory,
        "_fetch_real_host_data",
        lambda *args, **kw: _inventory.FetchedDataResult(
            parsed_sections_broker=ParsedSectionsBroker({}),
            source_results=[],
            parsing_errors=[],
            processing_failed=processing_failed,
            no_data_or_files=True,
        ),
    )

    monkeypatch.setattr(
        _inventory,
        "_inventorize_real_host",
        lambda *args, **kw: (
            InventoryTrees(
                inventory=StructuredDataNode(),
                status_data=StructuredDataNode(),
            ),
            UpdateResult(save_tree=False, reason=""),
        ),
    )

    check_result = _inventory.check_inventory_tree(
        hostname,
        host_config=HostConfig.make_host_config(hostname),
        selected_sections=NO_SELECTION,
        run_plugin_names=EVERYTHING,
        parameters=config.HWSWInventoryParameters.from_raw({}),
        old_tree=StructuredDataNode(),
    ).check_result

    assert check_result.state == 0
    assert check_result.summary == "No data yet, please be patient"
