#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

# pylint: disable=protected-access
from typing import List, Union

from cmk.utils.structured_data import StructuredDataNode

from cmk.base.agent_based import inventory
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow


def test_aggregator_raises_collision():
    inventory_items: List[Union[Attributes, TableRow]] = [
        Attributes(path=["a", "b", "c"], status_attributes={"foo": "bar"}),
        TableRow(path=["a", "b", "c"], key_columns={"foo": "bar"}),
    ]

    result = inventory.TreeAggregator().aggregate_results(inventory_items)

    assert isinstance(result, TypeError)
    assert str(result) == (
        "Cannot create TableRow at path ['a', 'b', 'c']: this is a Attributes node.")


_TREE_WITH_OTHER = StructuredDataNode()
_TREE_WITH_OTHER.setdefault_node(["other"])
_TREE_WITH_EDGE = StructuredDataNode()
_TREE_WITH_EDGE.setdefault_node(["edge"])


@pytest.mark.parametrize("old_tree, inv_tree", [
    (_TREE_WITH_OTHER, None),
    (_TREE_WITH_EDGE, None),
    (_TREE_WITH_EDGE, _TREE_WITH_OTHER),
    (_TREE_WITH_OTHER, _TREE_WITH_EDGE),
])
def test__tree_nodes_are_not_equal(old_tree, inv_tree):
    assert inventory._tree_nodes_are_equal(old_tree, inv_tree, "edge") is False


@pytest.mark.parametrize("old_tree, inv_tree", [
    (_TREE_WITH_OTHER, _TREE_WITH_OTHER),
    (_TREE_WITH_EDGE, _TREE_WITH_EDGE),
])
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
    tree_aggr.aggregate_results(inventory_items)

    assert tree_aggr.trees.inventory.serialize() == {
        'Attributes': {},
        'Nodes': {
            'a': {
                'Attributes': {},
                'Nodes': {
                    'b': {
                        'Attributes': {},
                        'Nodes': {
                            'c': {
                                'Attributes': {
                                    'Pairs': {
                                        'foo0': 'bar0',
                                        'foo1': 'bar1'
                                    }
                                },
                                'Nodes': {},
                                'Table': {}
                            }
                        },
                        'Table': {}
                    }
                },
                'Table': {}
            }
        },
        'Table': {}
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
    tree_aggr.aggregate_results(inventory_items)

    assert tree_aggr.trees.inventory.serialize() == {
        'Attributes': {},
        'Nodes': {
            'a': {
                'Attributes': {},
                'Nodes': {
                    'b': {
                        'Attributes': {},
                        'Nodes': {
                            'c': {
                                'Attributes': {},
                                'Nodes': {},
                                'Table': {
                                    'KeyColumns': ['foo'],
                                    'Rows': [
                                        {
                                            'col1': 'baz '
                                                    'val1',
                                            'col2': 'baz '
                                                    'val2',
                                            'col3': 'baz '
                                                    'val3',
                                            'foo': 'baz'
                                        },
                                        {
                                            'col1': 'new '
                                                    'bar '
                                                    'val1',
                                            'col2': 'bar '
                                                    'val2',
                                            'col3': 'bar '
                                                    'val3',
                                            'foo': 'bar'
                                        },
                                    ]
                                }
                            }
                        },
                        'Table': {}
                    }
                },
                'Table': {}
            }
        },
        'Table': {}
    }
