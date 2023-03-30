#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import logging
from collections.abc import Sequence
from typing import Literal

import pytest

from tests.testlib.base import Scenario

import cmk.utils.debug
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.structured_data import RetentionIntervals, StructuredDataNode, UpdateResult
from cmk.utils.type_defs import (
    AgentRawData,
    EVERYTHING,
    HostAddress,
    HostName,
    HWSWInventoryParameters,
    result,
)

from cmk.fetchers import FetcherType

from cmk.checkers import SourceInfo, SourceType
from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.type_defs import NO_SELECTION

import cmk.base.agent_based.inventory._inventory as _inventory
from cmk.base.agent_based.confcheckers import ConfiguredParser, SectionPluginMapper
from cmk.base.agent_based.inventory._active import _get_save_tree_actions, _SaveTreeActions
from cmk.base.agent_based.inventory._inventory import (
    _inventorize_real_host,
    _parse_inventory_plugin_item,
    ItemsOfInventoryPlugin,
)
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow


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


# TODO test cases:
# - items, raw intervals, previous node

# - items, raw intervals, no previous node
#       -> test__inventorize_real_host_only_intervals
#       -> test__inventorize_real_host_raw_cache_info_and_only_intervals

# - items, no raw intervals, previous node

# - items, no raw intervals, no previous node
#       -> test__inventorize_real_host_only_items

# - no items, raw intervals, previous node
#       -> test__inventorize_real_host_no_items

# - no items, raw intervals, no previous node
#       -> test__inventorize_real_host_no_items

# - no items, no raw intervals, previous node
#       -> test__inventorize_real_host_no_items

# - no items, no raw intervals, no previous node
#       -> test__inventorize_real_host_no_items


#   ---no previous node-----------------------------------------------------


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
    assert not bool(update_result.reasons_by_path)


@pytest.mark.parametrize(
    "attrs_choices, attrs_expected_retentions",
    [
        ("all", {"foo0": (10, 0, 3), "foo1": (10, 0, 3), "foo2": (10, 0, 3)}),
        ("nothing", {}),
        (("choices", ["foo0"]), {"foo0": (10, 0, 3)}),
        (("choices", ["unknown"]), {}),
    ],
)
@pytest.mark.parametrize(
    "table_choices, table_expected_retentions",
    [
        (
            "all",
            {
                ("bar0",): {"foo": (10, 0, 5), "col0": (10, 0, 5), "col1": (10, 0, 5)},
                ("bar1",): {"foo": (10, 0, 5), "col0": (10, 0, 5), "col1": (10, 0, 5)},
            },
        ),
        ("nothing", {}),
        (("choices", ["col0"]), {("bar0",): {"col0": (10, 0, 5)}, ("bar1",): {"col0": (10, 0, 5)}}),
        (("choices", ["unknown"]), {}),
    ],
)
def test__inventorize_real_host_only_intervals(
    attrs_choices: Literal["all"] | tuple[str, list[str]],
    attrs_expected_retentions: dict[str, tuple[int, int, int]],
    table_choices: Literal["all"] | tuple[str, list[str]],
    table_expected_retentions: dict[str, tuple[int, int, int]],
) -> None:
    trees, update_result = _inventorize_real_host(
        now=10,
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
        raw_intervals_from_config=[
            {
                "interval": 3,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": attrs_choices,
            },
            {
                "interval": 5,
                "visible_raw_path": "path-to.node-with-table",
                "columns": table_choices,
            },
        ],
        old_tree=StructuredDataNode(),
    )

    if attrs_expected_retentions:
        raw_attributes = {
            "Pairs": {
                "foo0": "bar0",
                "foo1": "2. bar1",
                "foo2": "bar2",
            },
            "Retentions": attrs_expected_retentions,
        }
    else:
        raw_attributes = {
            "Pairs": {
                "foo0": "bar0",
                "foo1": "2. bar1",
                "foo2": "bar2",
            },
        }

    if table_expected_retentions:
        table_retentions = {"Retentions": table_expected_retentions}
    else:
        table_retentions = {}

    assert trees.inventory.serialize() == {
        "Attributes": {},
        "Nodes": {
            "path-to": {
                "Attributes": {},
                "Nodes": {
                    "node-with-attrs": {
                        "Attributes": raw_attributes,
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
                            **table_retentions,
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

    if attrs_expected_retentions or table_expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)


@pytest.mark.parametrize(
    "attrs_choices, attrs_expected_retentions",
    [
        ("all", {"foo0": (1, 2, 3), "foo1": (1, 2, 3), "foo2": (1, 2, 3)}),
        ("nothing", {}),
        (("choices", ["foo0"]), {"foo0": (1, 2, 3)}),
        (("choices", ["unknown"]), {}),
    ],
)
@pytest.mark.parametrize(
    "table_choices, table_expected_retentions",
    [
        (
            "all",
            {
                ("bar0",): {"foo": (1, 2, 5), "col0": (1, 2, 5), "col1": (1, 2, 5)},
                ("bar1",): {"foo": (1, 2, 5), "col0": (1, 2, 5), "col1": (1, 2, 5)},
            },
        ),
        ("nothing", {}),
        (("choices", ["col0"]), {("bar0",): {"col0": (1, 2, 5)}, ("bar1",): {"col0": (1, 2, 5)}}),
        (("choices", ["unknown"]), {}),
    ],
)
def test__inventorize_real_host_raw_cache_info_and_only_intervals(
    attrs_choices: Literal["all"] | tuple[str, list[str]],
    attrs_expected_retentions: dict[str, tuple[int, int, int]],
    table_choices: Literal["all"] | tuple[str, list[str]],
    table_expected_retentions: dict[str, tuple[int, int, int]],
) -> None:
    trees, update_result = _inventorize_real_host(
        now=10,
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
                raw_cache_info=(1, 2),
            )
        ],
        raw_intervals_from_config=[
            {
                "interval": 3,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": attrs_choices,
            },
            {
                "interval": 5,
                "visible_raw_path": "path-to.node-with-table",
                "columns": table_choices,
            },
        ],
        old_tree=StructuredDataNode(),
    )

    if attrs_expected_retentions:
        raw_attributes = {
            "Pairs": {
                "foo0": "bar0",
                "foo1": "2. bar1",
                "foo2": "bar2",
            },
            "Retentions": attrs_expected_retentions,
        }
    else:
        raw_attributes = {
            "Pairs": {
                "foo0": "bar0",
                "foo1": "2. bar1",
                "foo2": "bar2",
            },
        }

    if table_expected_retentions:
        table_retentions = {"Retentions": table_expected_retentions}
    else:
        table_retentions = {}

    assert trees.inventory.serialize() == {
        "Attributes": {},
        "Nodes": {
            "path-to": {
                "Attributes": {},
                "Nodes": {
                    "node-with-attrs": {
                        "Attributes": raw_attributes,
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
                            **table_retentions,
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

    if attrs_expected_retentions or table_expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)


def _make_tree_or_items(
    *,
    previous_attributes_retentions: dict,
    previous_table_retentions: dict,
    raw_cache_info: tuple[int, int] | None,
) -> tuple[StructuredDataNode, list[ItemsOfInventoryPlugin]]:
    previous_tree = StructuredDataNode.deserialize(
        {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "path-to": {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "node-with-attrs": {
                            "Attributes": {
                                "Pairs": {"old": "Key", "keys": "Previous Keys"},
                                "Retentions": previous_attributes_retentions,
                            },
                            "Nodes": {},
                            "Table": {},
                        },
                        "node-with-table": {
                            "Attributes": {},
                            "Nodes": {},
                            "Table": {
                                "KeyColumns": ["ident"],
                                "Rows": [
                                    {"ident": "Ident 1", "old": "Key 1", "keys": "Previous Keys 1"},
                                    {"ident": "Ident 2", "old": "Key 2", "keys": "Previous Keys 2"},
                                ],
                                "Retentions": previous_table_retentions,
                            },
                        },
                    },
                }
            },
        }
    )
    items_of_inventory_plugins = [
        ItemsOfInventoryPlugin(
            items=[
                Attributes(
                    path=["path-to", "node-with-attrs"],
                    inventory_attributes={
                        "new": "Key",
                        "keys": "New Keys",
                    },
                ),
                TableRow(
                    path=["path-to", "node-with-table"],
                    key_columns={
                        "ident": "Ident 1",
                    },
                    inventory_columns={
                        "new": "Key 1",
                        "keys": "New Keys 1",
                    },
                ),
                TableRow(
                    path=["path-to", "node-with-table"],
                    key_columns={
                        "ident": "Ident 2",
                    },
                    inventory_columns={
                        "new": "Key 2",
                        "keys": "New Keys 2",
                    },
                ),
            ],
            raw_cache_info=raw_cache_info,
        ),
    ]
    return previous_tree, items_of_inventory_plugins


#   ---no items-------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_intervals",
    [
        [],
        [
            {
                "interval": 3,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": "all",
            },
            {
                "interval": 5,
                "visible_raw_path": "path-to.node-with-table",
                "columns": "all",
            },
        ],
    ],
)
@pytest.mark.parametrize(
    "previous_node, expected_inv_tree",
    [
        (StructuredDataNode(), StructuredDataNode()),
        (
            _make_tree_or_items(
                previous_attributes_retentions={},
                previous_table_retentions={},
                raw_cache_info=None,
            )[0],
            StructuredDataNode(),
        ),
        (
            _make_tree_or_items(
                previous_attributes_retentions={},
                previous_table_retentions={},
                raw_cache_info=(1, 2),
            )[0],
            StructuredDataNode(),
        ),
    ],
)
def test__inventorize_real_host_no_items(
    raw_intervals: list,
    previous_node: StructuredDataNode,
    expected_inv_tree: StructuredDataNode,
) -> None:
    trees, update_result = _inventorize_real_host(
        now=10,
        items_of_inventory_plugins=[],
        raw_intervals_from_config=raw_intervals,
        old_tree=previous_node,
    )

    assert trees.inventory.is_empty()
    assert trees.status_data.is_empty()

    assert not update_result.save_tree
    assert not bool(update_result.reasons_by_path)


#   ---previous node--------------------------------------------------------


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (("choices", ["old", "keyz"]), {"old": RetentionIntervals(1, 2, 3)}),
    ],
)
def test_updater_merge_previous_attributes(
    choices: tuple[str, list[str]],
    expected_retentions: dict,
) -> None:
    previous_tree, _items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={"old": (1, 2, 3)},
        previous_table_retentions={},
        raw_cache_info=(-1, -2),
    )
    trees, update_result = _inventorize_real_host(
        now=-1,
        items_of_inventory_plugins=[],
        raw_intervals_from_config=[
            {
                "interval": -3,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    previous_node = previous_tree.get_node(("path-to", "node-with-attrs"))
    assert previous_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)

    inv_node = inv_tree.get_node(("path-to", "node-with-attrs"))
    assert inv_node is not None
    assert inv_node.attributes.retentions == expected_retentions

    if expected_retentions:
        assert "old" in inv_node.attributes.pairs


@pytest.mark.parametrize(
    "choices",
    [
        ("choices", ["unknown", "keyz"]),
        ("choices", ["old", "keyz"]),
    ],
)
def test_updater_merge_previous_attributes_outdated(choices: tuple[str, list[str]]) -> None:
    previous_tree, _items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={"old": (1, 2, 3)},
        previous_table_retentions={},
        raw_cache_info=(-1, -2),
    )
    trees, update_result = _inventorize_real_host(
        now=1000,
        items_of_inventory_plugins=[],
        raw_intervals_from_config=[
            {
                "interval": -3,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    assert inv_tree.is_empty()

    previous_node = previous_tree.get_node(("path-to", "node-with-attrs"))
    assert isinstance(previous_node, StructuredDataNode)

    assert not update_result.save_tree
    assert not bool(update_result.reasons_by_path)

    inv_node = inv_tree.get_node(("path-to", "node-with-attrs"))
    assert inv_node is not None
    assert inv_node.attributes.retentions == {}


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (
            ("choices", ["old", "keyz"]),
            {
                ("Ident 1",): {"old": RetentionIntervals(1, 2, 3)},
                ("Ident 2",): {"old": RetentionIntervals(1, 2, 3)},
            },
        ),
    ],
)
def test_updater_merge_previous_tables(
    choices: tuple[str, list[str]],
    expected_retentions: dict,
) -> None:
    previous_tree, _items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {"old": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3)},
        },
        raw_cache_info=(-1, -2),
    )
    trees, update_result = _inventorize_real_host(
        now=-1,
        items_of_inventory_plugins=[],
        raw_intervals_from_config=[
            {
                "interval": -3,
                "visible_raw_path": "path-to.node-with-table",
                "columns": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    previous_node = previous_tree.get_node(("path-to", "node-with-table"))
    assert isinstance(previous_node, StructuredDataNode)

    if expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)

    inv_node = inv_tree.get_node(("path-to", "node-with-table"))
    assert inv_node is not None
    assert inv_node.table.retentions == expected_retentions

    if expected_retentions:
        for row in inv_node.table.rows:
            assert "old" in row


@pytest.mark.parametrize(
    "choices",
    [
        ("choices", ["unknown", "keyz"]),
        ("choices", ["old", "keyz"]),
    ],
)
def test_updater_merge_previous_tables_outdated(choices: tuple[str, list[str]]) -> None:
    previous_tree, _items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {"old": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3)},
        },
        raw_cache_info=(-1, -2),
    )
    trees, update_result = _inventorize_real_host(
        now=1000,
        items_of_inventory_plugins=[],
        raw_intervals_from_config=[
            {
                "interval": -3,
                "visible_raw_path": "path-to.node-with-table",
                "columns": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    assert inv_tree.is_empty()

    previous_node = previous_tree.get_node(("path-to", "node-with-table"))
    assert isinstance(previous_node, StructuredDataNode)

    assert not update_result.save_tree
    assert not bool(update_result.reasons_by_path)

    inv_node = inv_tree.get_node(("path-to", "node-with-table"))
    assert inv_node is not None
    assert inv_node.table.retentions == {}


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (
            ("choices", ["old", "and", "new", "keys"]),
            {
                "old": RetentionIntervals(1, 2, 3),
                "new": RetentionIntervals(4, 5, 6),
                "keys": RetentionIntervals(4, 5, 6),
            },
        ),
    ],
)
def test_updater_merge_attributes(
    choices: tuple[str, list[str]],
    expected_retentions: dict,
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={
            "old": (1, 2, 3),
            "keys": (1, 2, 3),
        },
        previous_table_retentions={},
        raw_cache_info=(4, 5),
    )
    trees, update_result = _inventorize_real_host(
        now=-1,
        items_of_inventory_plugins=items_of_inventory_plugins,
        raw_intervals_from_config=[
            {
                "interval": 6,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    previous_node = previous_tree.get_node(("path-to", "node-with-attrs"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node-with-attrs"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)

    assert inv_node.attributes.retentions == expected_retentions

    if expected_retentions:
        assert "old" in inv_node.attributes.pairs
        assert inv_node.attributes.pairs.get("keys") == "New Keys"


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (
            ("choices", ["old", "and", "new", "keys"]),
            {
                "new": RetentionIntervals(4, 5, 6),
                "keys": RetentionIntervals(4, 5, 6),
            },
        ),
    ],
)
def test_updater_merge_attributes_outdated(
    choices: tuple[str, list[str]],
    expected_retentions: dict,
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={
            "old": (1, 2, 3),
            "keys": (1, 2, 3),
        },
        previous_table_retentions={},
        raw_cache_info=(4, 5),
    )
    trees, update_result = _inventorize_real_host(
        now=1000,
        items_of_inventory_plugins=items_of_inventory_plugins,
        raw_intervals_from_config=[
            {
                "interval": 6,
                "visible_raw_path": "path-to.node-with-attrs",
                "attributes": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    previous_node = previous_tree.get_node(("path-to", "node-with-attrs"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node-with-attrs"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)

    assert inv_node.attributes.retentions == expected_retentions


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (
            ("choices", ["unknown", "keyz"]),
            {},
        ),
        (
            ("choices", ["old", "and", "new", "keys"]),
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
    choices: tuple[str, list[str]],
    expected_retentions: dict,
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {
                "old": (1, 2, 3),
                "keys": (1, 2, 3),
            },
            ("Ident 2",): {
                "old": (1, 2, 3),
                "keys": (1, 2, 3),
            },
        },
        raw_cache_info=(4, 5),
    )
    trees, update_result = _inventorize_real_host(
        now=-1,
        items_of_inventory_plugins=items_of_inventory_plugins,
        raw_intervals_from_config=[
            {
                "interval": 6,
                "visible_raw_path": "path-to.node-with-table",
                "columns": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    previous_node = previous_tree.get_node(("path-to", "node-with-table"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node-with-table"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)

    assert inv_node.table.retentions == expected_retentions

    if expected_retentions:
        for row in inv_node.table.rows:
            assert "old" in row
            assert row["keys"].startswith("New Keys")


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (
            ("choices", ["unknown", "keyz"]),
            {},
        ),
        (
            ("choices", ["old", "and", "new", "keys"]),
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
    choices: tuple[str, list[str]],
    expected_retentions: dict,
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {"old": (1, 2, 3), "keys": (1, 2, 3)},
            ("Ident 2",): {"old": (1, 2, 3), "keys": (1, 2, 3)},
        },
        raw_cache_info=(4, 5),
    )
    trees, update_result = _inventorize_real_host(
        now=1000,
        items_of_inventory_plugins=items_of_inventory_plugins,
        raw_intervals_from_config=[
            {
                "interval": 6,
                "visible_raw_path": "path-to.node-with-table",
                "columns": choices,
            }
        ],
        old_tree=previous_tree,
    )
    inv_tree = trees.inventory

    previous_node = previous_tree.get_node(("path-to", "node-with-table"))
    assert previous_node is not None

    inv_node = inv_tree.get_node(("path-to", "node-with-table"))
    assert inv_node is not None

    if expected_retentions:
        assert update_result.save_tree
        assert bool(update_result.reasons_by_path)
    else:
        assert not update_result.save_tree
        assert not bool(update_result.reasons_by_path)

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
def test_inventorize_host(
    monkeypatch: pytest.MonkeyPatch,
    failed_state: int | None,
    expected: int,
) -> None:
    def fetcher(
        host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[tuple[SourceInfo, result.Result[AgentRawData, Exception], Snapshot]]:
        return [
            (
                SourceInfo(hostname, None, "ident", FetcherType.TCP, SourceType.HOST),
                result.Error(Exception()),
                Snapshot.null(),
            ),
            (
                SourceInfo(hostname, None, "ident", FetcherType.TCP, SourceType.HOST),
                result.OK(AgentRawData(b"<<<data>>>")),
                Snapshot.null(),
            ),
        ]

    hostname = HostName("my-host")
    config_cache = Scenario().apply(monkeypatch)
    parser = ConfiguredParser(
        config_cache,
        selected_sections=NO_SELECTION,
        keep_outdated=True,
        logger=logging.getLogger("tests"),
    )
    check_result = _inventory.inventorize_host(
        hostname,
        fetcher=fetcher,
        parser=parser,
        summarizer=lambda *args, **kwargs: [],
        inventory_parameters=lambda *args, **kw: {},
        section_plugins=SectionPluginMapper(),
        inventory_plugins={},
        run_plugin_names=EVERYTHING,
        parameters=HWSWInventoryParameters.from_raw(
            {} if failed_state is None else {"inv-fail-status": failed_state}
        ),
        raw_intervals_from_config=(),
        old_tree=StructuredDataNode(),
    ).check_result

    assert expected == check_result.state
    assert "Did not update the tree due to at least one error" in check_result.summary


def test_inventorize_host_with_no_data_nor_files() -> None:
    hostname = HostName("my-host")
    check_result = _inventory.inventorize_host(
        hostname,
        # no data!
        fetcher=lambda *args, **kwargs: [],
        parser=lambda *args, **kwargs: [],
        summarizer=lambda *args, **kwargs: [],
        inventory_parameters=lambda *args, **kw: {},
        section_plugins={},
        inventory_plugins={},
        run_plugin_names=EVERYTHING,
        parameters=HWSWInventoryParameters.from_raw({}),
        raw_intervals_from_config=(),
        old_tree=StructuredDataNode(),
    ).check_result

    assert check_result.state == 0
    assert check_result.summary == "No data yet, please be patient"


@pytest.mark.parametrize(
    "inventory_tree, active_check_results",
    [
        (
            StructuredDataNode.deserialize(
                {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {},
                }
            ),
            [
                ActiveCheckResult(
                    state=1,
                    summary="Did not update the tree due to at least one error",
                    details=(),
                    metrics=(),
                ),
                ActiveCheckResult(state=0, summary="Found no data", details=(), metrics=()),
            ],
        ),
        (
            StructuredDataNode.deserialize(
                {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "software": {
                            "Attributes": {},
                            "Table": {},
                            "Nodes": {
                                "applications": {
                                    "Attributes": {},
                                    "Table": {},
                                    "Nodes": {
                                        "check_mk": {
                                            "Attributes": {},
                                            "Table": {},
                                            "Nodes": {
                                                "cluster": {
                                                    "Attributes": {
                                                        "Pairs": {"is_cluster": True, "foo": "bar"}
                                                    },
                                                    "Table": {},
                                                    "Nodes": {},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        }
                    },
                }
            ),
            [
                ActiveCheckResult(
                    state=1,
                    summary="Did not update the tree due to at least one error",
                    details=(),
                    metrics=(),
                ),
                ActiveCheckResult(
                    state=0, summary="Found 2 inventory entries", details=(), metrics=()
                ),
                ActiveCheckResult(state=0, summary="software changes", details=(), metrics=()),
            ],
        ),
        (
            StructuredDataNode.deserialize(
                {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "software": {
                            "Attributes": {},
                            "Table": {},
                            "Nodes": {
                                "applications": {
                                    "Attributes": {},
                                    "Table": {},
                                    "Nodes": {
                                        "check_mk": {
                                            "Attributes": {},
                                            "Table": {},
                                            "Nodes": {
                                                "cluster": {
                                                    "Attributes": {"Pairs": {"is_cluster": True}},
                                                    "Table": {},
                                                    "Nodes": {},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        }
                    },
                }
            ),
            [
                ActiveCheckResult(
                    state=0, summary="No further data for tree update", details=(), metrics=()
                ),
                ActiveCheckResult(
                    state=0, summary="Found 1 inventory entries", details=(), metrics=()
                ),
                ActiveCheckResult(state=0, summary="software changes", details=(), metrics=()),
            ],
        ),
        (
            StructuredDataNode.deserialize(
                {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "software": {
                            "Attributes": {},
                            "Table": {},
                            "Nodes": {
                                "applications": {
                                    "Attributes": {},
                                    "Table": {},
                                    "Nodes": {
                                        "check_mk": {
                                            "Attributes": {},
                                            "Table": {},
                                            "Nodes": {
                                                "cluster": {
                                                    "Attributes": {"Pairs": {"is_cluster": False}},
                                                    "Table": {},
                                                    "Nodes": {},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        }
                    },
                }
            ),
            [
                ActiveCheckResult(
                    state=0, summary="No further data for tree update", details=(), metrics=()
                ),
                ActiveCheckResult(
                    state=0, summary="Found 1 inventory entries", details=(), metrics=()
                ),
                ActiveCheckResult(state=0, summary="software changes", details=(), metrics=()),
            ],
        ),
    ],
)
def test__check_fetched_data_or_trees_only_cluster_property(
    inventory_tree: StructuredDataNode, active_check_results: Sequence[ActiveCheckResult]
) -> None:
    assert (
        list(
            _inventory._check_fetched_data_or_trees(
                parameters=HWSWInventoryParameters.from_raw({}),
                inventory_tree=inventory_tree,
                status_data_tree=StructuredDataNode.deserialize({}),
                old_tree=StructuredDataNode.deserialize({}),
                no_data_or_files=False,
                processing_failed=True,
            )
        )
        == active_check_results
    )


@pytest.mark.parametrize(
    "old_tree, inventory_tree, update_result, expected_save_tree_actions",
    [
        (
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "old value"}}, "Table": {}, "Nodes": {}}
            ),
            # No further impact, may not be realistic here
            StructuredDataNode(),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={("path-to", "node"): []}),
            _SaveTreeActions(do_archive=True, do_save=False),
        ),
        (
            StructuredDataNode(),
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "new value"}}, "Table": {}, "Nodes": {}}
            ),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={("path-to", "node"): []}),
            _SaveTreeActions(do_archive=False, do_save=True),
        ),
        (
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "old value"}}, "Table": {}, "Nodes": {}}
            ),
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "new value"}}, "Table": {}, "Nodes": {}}
            ),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={("path-to", "node"): []}),
            _SaveTreeActions(do_archive=True, do_save=True),
        ),
        (
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "old value"}}, "Table": {}, "Nodes": {}}
            ),
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "new value"}}, "Table": {}, "Nodes": {}}
            ),
            UpdateResult(),
            _SaveTreeActions(do_archive=True, do_save=True),
        ),
        (
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "value"}}, "Table": {}, "Nodes": {}}
            ),
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "value"}}, "Table": {}, "Nodes": {}}
            ),
            UpdateResult(),
            _SaveTreeActions(do_archive=False, do_save=False),
        ),
        (
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "value"}}, "Table": {}, "Nodes": {}}
            ),
            StructuredDataNode.deserialize(
                {"Attributes": {"Pairs": {"key": "value"}}, "Table": {}, "Nodes": {}}
            ),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={("path-to", "node"): []}),
            _SaveTreeActions(do_archive=False, do_save=True),
        ),
    ],
)
def test_save_tree_actions(
    old_tree: StructuredDataNode,
    inventory_tree: StructuredDataNode,
    update_result: UpdateResult,
    expected_save_tree_actions: _SaveTreeActions,
) -> None:
    assert (
        _get_save_tree_actions(
            old_tree=old_tree,
            inventory_tree=inventory_tree,
            update_result=update_result,
        )
        == expected_save_tree_actions
    )
