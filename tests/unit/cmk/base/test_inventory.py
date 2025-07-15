#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

import pytest

import cmk.ccc.resulttype as result
from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.structured_data import (
    _serialize_retention_interval,
    deserialize_tree,
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    MutableTree,
    RetentionInterval,
    SDKey,
    SDNodeName,
    SDRowIdent,
    serialize_tree,
    UpdateResult,
)

from cmk.snmplib import SNMPRawData

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.fetcher import FetcherType, SourceInfo, SourceType
from cmk.checkengine.inventory import (
    _check_fetched_data_or_trees,
    _create_trees_from_inventory_plugin_items,
    _inventorize_real_host,
    _parse_inventory_plugin_item,
    HWSWInventoryParameters,
    inventorize_host,
    ItemsOfInventoryPlugin,
)
from cmk.checkengine.parser import HostSections
from cmk.checkengine.sectionparser import ParsedSectionName, SectionPlugin

from cmk.base.modes.check_mk import _get_save_tree_actions, _SaveTreeActions

from cmk.agent_based.v1 import Attributes, TableRow


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


@pytest.mark.parametrize(
    "item, known_class_name",
    [
        (Attributes(path=["a", "b", "c"], status_attributes={"foo": "bar"}), "TableRow"),
        (TableRow(path=["a", "b", "c"], key_columns={"foo": "bar"}), "Attributes"),
    ],
)
def test_item_collisions(item: Attributes | TableRow, known_class_name: str) -> None:
    with pytest.raises(TypeError) as e:
        _parse_inventory_plugin_item(item, known_class_name)

        assert str(e) == (
            "Cannot create TableRow at path ['a', 'b', 'c']: this is a Attributes node."
        )


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
        previous_tree=ImmutableTree(),
    )

    assert serialize_tree(trees.inventory) == {
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
    assert not update_result.reasons_by_path


@pytest.mark.parametrize(
    "attrs_choices, attrs_expected_retentions",
    [
        (
            "all",
            {
                "foo0": RetentionInterval(10, 0, 3, "current"),
                "foo1": RetentionInterval(10, 0, 3, "current"),
                "foo2": RetentionInterval(10, 0, 3, "current"),
            },
        ),
        ("nothing", {}),
        (("choices", ["foo0"]), {"foo0": RetentionInterval(10, 0, 3, "current")}),
        (("choices", ["unknown"]), {}),
    ],
)
@pytest.mark.parametrize(
    "table_choices, table_expected_retentions",
    [
        (
            "all",
            {
                ("bar0",): {
                    "foo": RetentionInterval(10, 0, 5, "current"),
                    "col0": RetentionInterval(10, 0, 5, "current"),
                    "col1": RetentionInterval(10, 0, 5, "current"),
                },
                ("bar1",): {
                    "foo": RetentionInterval(10, 0, 5, "current"),
                    "col0": RetentionInterval(10, 0, 5, "current"),
                    "col1": RetentionInterval(10, 0, 5, "current"),
                },
            },
        ),
        ("nothing", {}),
        (
            ("choices", ["col0"]),
            {
                ("bar0",): {"col0": RetentionInterval(10, 0, 5, "current")},
                ("bar1",): {"col0": RetentionInterval(10, 0, 5, "current")},
            },
        ),
        (("choices", ["unknown"]), {}),
    ],
)
def test__inventorize_real_host_only_intervals(
    attrs_choices: Literal["all"] | tuple[str, list[str]],
    attrs_expected_retentions: Mapping[SDKey, RetentionInterval],
    table_choices: Literal["all"] | tuple[str, list[str]],
    table_expected_retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
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
        previous_tree=ImmutableTree(),
    )

    if attrs_expected_retentions:
        raw_attributes = {
            "Pairs": {
                "foo0": "bar0",
                "foo1": "2. bar1",
                "foo2": "bar2",
            },
            "Retentions": {
                k: _serialize_retention_interval(v) for k, v in attrs_expected_retentions.items()
            },
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
        table_retentions = {
            "Retentions": {
                i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
                for i, ri in table_expected_retentions.items()
            }
        }
    else:
        table_retentions = {}

    assert serialize_tree(trees.inventory) == {
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
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path


@pytest.mark.parametrize(
    "attrs_choices, attrs_expected_retentions",
    [
        (
            "all",
            {
                "foo0": RetentionInterval(1, 2, 3, "current"),
                "foo1": RetentionInterval(1, 2, 3, "current"),
                "foo2": RetentionInterval(1, 2, 3, "current"),
            },
        ),
        ("nothing", {}),
        (("choices", ["foo0"]), {"foo0": RetentionInterval(1, 2, 3, "current")}),
        (("choices", ["unknown"]), {}),
    ],
)
@pytest.mark.parametrize(
    "table_choices, table_expected_retentions",
    [
        (
            "all",
            {
                ("bar0",): {
                    "foo": RetentionInterval(1, 2, 5, "current"),
                    "col0": RetentionInterval(1, 2, 5, "current"),
                    "col1": RetentionInterval(1, 2, 5, "current"),
                },
                ("bar1",): {
                    "foo": RetentionInterval(1, 2, 5, "current"),
                    "col0": RetentionInterval(1, 2, 5, "current"),
                    "col1": RetentionInterval(1, 2, 5, "current"),
                },
            },
        ),
        ("nothing", {}),
        (
            ("choices", ["col0"]),
            {
                ("bar0",): {"col0": RetentionInterval(1, 2, 5, "current")},
                ("bar1",): {"col0": RetentionInterval(1, 2, 5, "current")},
            },
        ),
        (("choices", ["unknown"]), {}),
    ],
)
def test__inventorize_real_host_raw_cache_info_and_only_intervals(
    attrs_choices: Literal["all"] | tuple[str, list[str]],
    attrs_expected_retentions: Mapping[SDKey, RetentionInterval],
    table_choices: Literal["all"] | tuple[str, list[str]],
    table_expected_retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
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
        previous_tree=ImmutableTree(),
    )

    if attrs_expected_retentions:
        raw_attributes = {
            "Pairs": {
                "foo0": "bar0",
                "foo1": "2. bar1",
                "foo2": "bar2",
            },
            "Retentions": {
                k: _serialize_retention_interval(v) for k, v in attrs_expected_retentions.items()
            },
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
        table_retentions = {
            "Retentions": {
                i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
                for i, ri in table_expected_retentions.items()
            }
        }
    else:
        table_retentions = {}

    assert serialize_tree(trees.inventory) == {
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
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path


def _make_tree_or_items(
    *,
    previous_attributes_retentions: Mapping[SDKey, RetentionInterval],
    previous_table_retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
    raw_cache_info: tuple[int, int] | None,
) -> tuple[ImmutableTree, list[ItemsOfInventoryPlugin]]:
    previous_tree = deserialize_tree(
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
                                "Retentions": {
                                    k: _serialize_retention_interval(v)
                                    for k, v in previous_attributes_retentions.items()
                                },
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
                                    {
                                        "ident": "Ident 1",
                                        "old": "Key 1",
                                        "keys": "Previous Keys 1",
                                    },
                                    {
                                        "ident": "Ident 2",
                                        "old": "Key 2",
                                        "keys": "Previous Keys 2",
                                    },
                                ],
                                "Retentions": {
                                    i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
                                    for i, ri in previous_table_retentions.items()
                                },
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
    "previous_node",
    [
        ImmutableTree(),
        _make_tree_or_items(
            previous_attributes_retentions={},
            previous_table_retentions={},
            raw_cache_info=None,
        )[0],
        _make_tree_or_items(
            previous_attributes_retentions={},
            previous_table_retentions={},
            raw_cache_info=(1, 2),
        )[0],
    ],
)
def test__inventorize_real_host_no_items(
    raw_intervals: list,
    previous_node: ImmutableTree,
) -> None:
    trees, update_result = _inventorize_real_host(
        now=10,
        items_of_inventory_plugins=[],
        raw_intervals_from_config=raw_intervals,
        previous_tree=previous_node,
    )

    assert not trees.inventory
    assert not trees.status_data

    assert not update_result.save_tree
    assert not update_result.reasons_by_path


#   ---previous node--------------------------------------------------------


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (("choices", ["old", "keyz"]), {"old": RetentionInterval(1, 2, 3, "previous")}),
    ],
)
def test_updater_merge_previous_attributes(
    choices: tuple[str, list[str]],
    expected_retentions: Mapping[SDKey, RetentionInterval],
) -> None:
    previous_tree, _items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={SDKey("old"): RetentionInterval(1, 2, 3, "current")},
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
        previous_tree=previous_tree,
    )

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-attrs")))
    )
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
        previous_attributes_retentions={SDKey("old"): RetentionInterval(1, 2, 3, "current")},
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
        previous_tree=previous_tree,
    )
    assert not trees.inventory

    assert not update_result.save_tree
    assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-attrs")))
    )
    assert inv_node.attributes.retentions == {}


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (
            ("choices", ["old", "keyz"]),
            {
                ("Ident 1",): {"old": RetentionInterval(1, 2, 3, "previous")},
                ("Ident 2",): {"old": RetentionInterval(1, 2, 3, "previous")},
            },
        ),
    ],
)
def test_updater_merge_previous_tables(
    choices: tuple[str, list[str]],
    expected_retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
) -> None:
    previous_tree, _items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {SDKey("old"): RetentionInterval(1, 2, 3, "current")},
            ("Ident 2",): {SDKey("old"): RetentionInterval(1, 2, 3, "current")},
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
        previous_tree=previous_tree,
    )

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-table")))
    )
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
            ("Ident 1",): {SDKey("old"): RetentionInterval(1, 2, 3, "current")},
            ("Ident 2",): {SDKey("old"): RetentionInterval(1, 2, 3, "current")},
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
        previous_tree=previous_tree,
    )

    assert not trees.inventory
    assert not update_result.save_tree
    assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-table")))
    )
    assert inv_node.table.retentions == {}


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (
            ("choices", ["old", "and", "new", "keys"]),
            {
                "old": RetentionInterval(1, 2, 3, "previous"),
                "new": RetentionInterval(4, 5, 6, "current"),
                "keys": RetentionInterval(4, 5, 6, "current"),
            },
        ),
    ],
)
def test_updater_merge_attributes(
    choices: tuple[str, list[str]],
    expected_retentions: Mapping[SDKey, RetentionInterval],
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={
            SDKey("old"): RetentionInterval(1, 2, 3, "current"),
            SDKey("keys"): RetentionInterval(1, 2, 3, "current"),
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
        previous_tree=previous_tree,
    )

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-attrs")))
    )
    assert inv_node.attributes.retentions == expected_retentions

    if expected_retentions:
        assert "old" in inv_node.attributes.pairs
        assert inv_node.attributes.pairs.get(SDKey("keys")) == "New Keys"


@pytest.mark.parametrize(
    "choices, expected_retentions",
    [
        (("choices", ["unknown", "keyz"]), {}),
        (
            ("choices", ["old", "and", "new", "keys"]),
            {
                "new": RetentionInterval(4, 5, 6, "current"),
                "keys": RetentionInterval(4, 5, 6, "current"),
            },
        ),
    ],
)
def test_updater_merge_attributes_outdated(
    choices: tuple[str, list[str]],
    expected_retentions: Mapping[SDKey, RetentionInterval],
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={
            SDKey("old"): RetentionInterval(1, 2, 3, "current"),
            SDKey("keys"): RetentionInterval(1, 2, 3, "current"),
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
        previous_tree=previous_tree,
    )

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-attrs")))
    )
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
                    "old": RetentionInterval(1, 2, 3, "previous"),
                    "new": RetentionInterval(4, 5, 6, "current"),
                    "keys": RetentionInterval(4, 5, 6, "current"),
                },
                ("Ident 2",): {
                    "old": RetentionInterval(1, 2, 3, "previous"),
                    "new": RetentionInterval(4, 5, 6, "current"),
                    "keys": RetentionInterval(4, 5, 6, "current"),
                },
            },
        ),
    ],
)
def test_updater_merge_tables(
    choices: tuple[str, list[str]],
    expected_retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {
                SDKey("old"): RetentionInterval(1, 2, 3, "current"),
                SDKey("keys"): RetentionInterval(1, 2, 3, "current"),
            },
            ("Ident 2",): {
                SDKey("old"): RetentionInterval(1, 2, 3, "current"),
                SDKey("keys"): RetentionInterval(1, 2, 3, "current"),
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
        previous_tree=previous_tree,
    )

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-table")))
    )
    assert inv_node.table.retentions == expected_retentions

    if expected_retentions:
        for row in inv_node.table.rows:
            assert "old" in row
            assert isinstance(v := row[SDKey("keys")], str)
            assert v.startswith("New Keys")


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
                    "new": RetentionInterval(4, 5, 6, "current"),
                    "keys": RetentionInterval(4, 5, 6, "current"),
                },
                ("Ident 2",): {
                    "new": RetentionInterval(4, 5, 6, "current"),
                    "keys": RetentionInterval(4, 5, 6, "current"),
                },
            },
        ),
    ],
)
def test_updater_merge_tables_outdated(
    choices: tuple[str, list[str]],
    expected_retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
) -> None:
    previous_tree, items_of_inventory_plugins = _make_tree_or_items(
        previous_attributes_retentions={},
        previous_table_retentions={
            ("Ident 1",): {
                SDKey("old"): RetentionInterval(1, 2, 3, "current"),
                SDKey("keys"): RetentionInterval(1, 2, 3, "current"),
            },
            ("Ident 2",): {
                SDKey("old"): RetentionInterval(1, 2, 3, "current"),
                SDKey("keys"): RetentionInterval(1, 2, 3, "current"),
            },
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
        previous_tree=previous_tree,
    )

    if expected_retentions:
        assert update_result.save_tree
        assert update_result.reasons_by_path
    else:
        assert not update_result.save_tree
        assert not update_result.reasons_by_path

    inv_node = _make_immutable_tree(
        trees.inventory.get_tree((SDNodeName("path-to"), SDNodeName("node-with-table")))
    )
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
def test_inventorize_host(failed_state: int | None, expected: int) -> None:
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

    def parser(
        fetched: Iterable[
            tuple[
                SourceInfo,
                result.Result[AgentRawData | SNMPRawData, Exception],
            ]
        ],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        def parse(
            header: AgentRawData | SNMPRawData,
        ) -> SectionMap[str]:
            assert isinstance(header, bytes)
            txt = header.decode()
            return {SectionName(txt[3:-3]): txt}

        return [
            (
                source_info,
                (
                    result.Error(res.error)
                    if res.is_error()
                    else res.map(lambda ok: HostSections(parse(ok)))
                ),
            )
            for source_info, res in fetched
        ]

    hostname = HostName("my-host")

    check_results = inventorize_host(
        hostname,
        fetcher=fetcher,
        parser=parser,
        summarizer=lambda *args, **kwargs: [],
        inventory_parameters=lambda *args, **kw: {},
        section_plugins={
            SectionName("data"): SectionPlugin(
                supersedes=set(),
                parse_function=lambda *args, **kw: object,
                parsed_section_name=ParsedSectionName("data"),
            )
        },
        section_error_handling=lambda *args, **kw: "error",
        inventory_plugins={},
        run_plugin_names=EVERYTHING,
        parameters=HWSWInventoryParameters.from_raw(
            {} if failed_state is None else {"inv-fail-status": failed_state}
        ),
        raw_intervals_from_config=(),
        previous_tree=ImmutableTree(),
    ).check_results

    check_result = ActiveCheckResult.from_subresults(*check_results)
    assert expected == check_result.state
    assert "Did not update the tree due to at least one error" in check_result.summary


def test_inventorize_host_with_no_data_nor_files() -> None:
    hostname = HostName("my-host")
    check_results = inventorize_host(
        hostname,
        # no data!
        fetcher=lambda *args, **kwargs: [],
        parser=lambda *args, **kwargs: [],
        summarizer=lambda *args, **kwargs: [],
        inventory_parameters=lambda *args, **kw: {},
        section_plugins={},
        section_error_handling=lambda *args, **kw: "error",
        inventory_plugins={},
        run_plugin_names=EVERYTHING,
        parameters=HWSWInventoryParameters.from_raw({}),
        raw_intervals_from_config=(),
        previous_tree=ImmutableTree(),
    ).check_results

    check_result = ActiveCheckResult.from_subresults(*check_results)
    assert check_result.state == 0
    assert check_result.summary == "No data yet, please be patient"


def _create_cluster_tree(pairs: Mapping[SDKey, int | float | str | None]) -> MutableTree:
    tree = MutableTree()
    tree.add(
        path=(
            SDNodeName("software"),
            SDNodeName("applications"),
            SDNodeName("check_mk"),
            SDNodeName("cluster"),
        ),
        pairs=[pairs],
    )
    return tree


@pytest.mark.parametrize(
    "inventory_tree, active_check_results",
    [
        (
            MutableTree(),
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
            _create_cluster_tree({SDKey("is_cluster"): True, SDKey("foo"): "bar"}),
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
            _create_cluster_tree({SDKey("is_cluster"): True}),
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
            _create_cluster_tree({SDKey("is_cluster"): False}),
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
    inventory_tree: MutableTree, active_check_results: Sequence[ActiveCheckResult]
) -> None:
    assert (
        list(
            _check_fetched_data_or_trees(
                parameters=HWSWInventoryParameters.from_raw({}),
                inventory_tree=inventory_tree,
                status_data_tree=MutableTree(),
                previous_tree=ImmutableTree(),
                no_data_or_files=False,
                processing_failed=True,
            )
        )
        == active_check_results
    )


def _create_root_tree(pairs: Mapping[SDKey, int | float | str | None]) -> MutableTree:
    tree = MutableTree()
    tree.add(path=(), pairs=[pairs])
    return tree


@pytest.mark.parametrize(
    "previous_tree, inventory_tree, update_result, expected_save_tree_actions",
    [
        (
            deserialize_tree(
                {
                    "Attributes": {"Pairs": {"key": "old value"}},
                    "Table": {},
                    "Nodes": {},
                }
            ),
            # No further impact, may not be realistic here
            MutableTree(),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={(SDNodeName("path-to"), SDNodeName("node")): []}),
            _SaveTreeActions(do_archive=True, do_save=False),
        ),
        (
            ImmutableTree(),
            _create_root_tree({SDKey("key"): "new value"}),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={(SDNodeName("path-to"), SDNodeName("node")): []}),
            _SaveTreeActions(do_archive=False, do_save=True),
        ),
        (
            deserialize_tree(
                {
                    "Attributes": {"Pairs": {"key": "old value"}},
                    "Table": {},
                    "Nodes": {},
                }
            ),
            _create_root_tree({SDKey("key"): "new value"}),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={(SDNodeName("path-to"), SDNodeName("node")): []}),
            _SaveTreeActions(do_archive=True, do_save=True),
        ),
        (
            deserialize_tree(
                {
                    "Attributes": {"Pairs": {"key": "old value"}},
                    "Table": {},
                    "Nodes": {},
                }
            ),
            _create_root_tree({SDKey("key"): "new value"}),
            UpdateResult(),
            _SaveTreeActions(do_archive=True, do_save=True),
        ),
        (
            deserialize_tree({"Attributes": {"Pairs": {"key": "value"}}, "Table": {}, "Nodes": {}}),
            _create_root_tree({SDKey("key"): "value"}),
            UpdateResult(),
            _SaveTreeActions(do_archive=False, do_save=False),
        ),
        (
            deserialize_tree({"Attributes": {"Pairs": {"key": "value"}}, "Table": {}, "Nodes": {}}),
            _create_root_tree({SDKey("key"): "value"}),
            # Content of path does not matter here
            UpdateResult(reasons_by_path={(SDNodeName("path-to"), SDNodeName("node")): []}),
            _SaveTreeActions(do_archive=False, do_save=True),
        ),
    ],
)
def test_save_tree_actions(
    previous_tree: ImmutableTree,
    inventory_tree: MutableTree,
    update_result: UpdateResult,
    expected_save_tree_actions: _SaveTreeActions,
) -> None:
    assert (
        _get_save_tree_actions(
            previous_tree=previous_tree,
            inventory_tree=inventory_tree,
            update_result=update_result,
        )
        == expected_save_tree_actions
    )


def test_add_rows_with_different_key_columns() -> None:
    trees = _create_trees_from_inventory_plugin_items(
        [
            ItemsOfInventoryPlugin(
                items=[
                    TableRow(
                        path=["path-to-node"],
                        key_columns={
                            "ident": "Ident 1",
                        },
                        inventory_columns={
                            "key": "Key 1",
                        },
                    ),
                    TableRow(
                        path=["path-to-node"],
                        key_columns={
                            "another-ident": "Another ident 2",
                        },
                        inventory_columns={
                            "key": "Key 2",
                        },
                    ),
                    TableRow(
                        path=["path-to-node"],
                        key_columns={
                            "ident": "Ident 3",
                            "another-ident": "Another ident 3",
                        },
                        inventory_columns={
                            "key": "Key 3",
                        },
                    ),
                    TableRow(
                        path=["path-to-node"],
                        key_columns={
                            "ident": "Ident 1",
                        },
                        inventory_columns={
                            "another-key": "Another key 1",
                        },
                    ),
                ],
                raw_cache_info=(1, 2),
            ),
        ]
    )
    tree_from_fs = deserialize_tree(serialize_tree(trees.inventory))
    assert tree_from_fs == trees.inventory
    rows = tree_from_fs.get_rows((SDNodeName("path-to-node"),))
    assert len(rows) == 3
    for row in [
        {"ident": "Ident 1", "key": "Key 1", "another-key": "Another key 1"},
        {"another-ident": "Another ident 2", "key": "Key 2"},
        {"another-ident": "Another ident 3", "ident": "Ident 3", "key": "Key 3"},
    ]:
        assert row in rows
