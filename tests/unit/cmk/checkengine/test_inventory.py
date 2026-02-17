#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1 import TableRow
from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.inventory import (
    _check_trees,
    _create_trees_from_inventory_plugin_items,
    HWSWInventoryParameters,
    ItemsOfInventoryPlugin,
)
from cmk.inventory.structured_data import ImmutableTree, MutableTree, SDKey, SDNodeName


@pytest.mark.parametrize(
    "parameters, expected_results",
    [
        pytest.param(
            HWSWInventoryParameters(0, 0, 0, 0, 0, False),
            [
                ActiveCheckResult(
                    state=0,
                    summary="Found 2 inventory entries",
                    details=(),
                    metrics=(),
                ),
            ],
            id="OK",
        ),
        pytest.param(
            HWSWInventoryParameters(0, 0, 1, 0, 0, False),
            [
                ActiveCheckResult(
                    state=0,
                    summary="Found 2 inventory entries",
                    details=(),
                    metrics=(),
                ),
                ActiveCheckResult(
                    state=1,
                    summary="software packages information is missing",
                    details=(),
                    metrics=(),
                ),
            ],
            id="missing-sw",
        ),
    ],
)
def test__check_trees(
    parameters: HWSWInventoryParameters, expected_results: Sequence[ActiveCheckResult]
) -> None:
    inventory_tree = MutableTree()
    inventory_tree.add(path=(), pairs=[{SDKey("a"): "A", SDKey("b"): "B"}])
    assert (
        list(
            _check_trees(
                parameters=parameters,
                inventory_tree=inventory_tree,
                status_data_tree=MutableTree(),
                previous_tree=ImmutableTree(),
            )
        )
        == expected_results
    )


def test__check_trees_hardware_or_software_changes() -> None:
    inventory_tree = MutableTree()
    inventory_tree.add(
        path=(SDNodeName("hardware"),),
        pairs=[{SDKey("h1"): "H 1", SDKey("h2"): "H 2"}],
    )
    inventory_tree.add(
        path=(SDNodeName("software"),),
        pairs=[{SDKey("s1"): "S 1", SDKey("s2"): "S 2"}],
    )
    inventory_tree.add(
        path=(SDNodeName("networking"),),
        pairs=[{SDKey("n1"): "N 1", SDKey("n2"): "N 2"}],
    )
    assert list(
        _check_trees(
            parameters=HWSWInventoryParameters(1, 2, 0, 3, 0, False),
            inventory_tree=inventory_tree,
            status_data_tree=MutableTree(),
            previous_tree=ImmutableTree(),
        )
    ) == [
        ActiveCheckResult(
            state=0,
            summary="Found 6 inventory entries",
            details=(),
            metrics=(),
        ),
        ActiveCheckResult(
            state=2,
            summary="software changes",
            details=(),
            metrics=(),
        ),
        ActiveCheckResult(
            state=1,
            summary="hardware changes",
            details=(),
            metrics=(),
        ),
        ActiveCheckResult(
            state=3,
            summary="networking changes",
            details=(),
            metrics=(),
        ),
    ]


def test__create_trees_from_inventory_plugin_items_only_key_columns() -> None:
    trees = _create_trees_from_inventory_plugin_items(
        [
            ItemsOfInventoryPlugin(
                [
                    TableRow(
                        path=["path-to-node"],
                        key_columns={"key": "value"},
                    )
                ],
                None,
            ),
        ]
    )
    assert trees.inventory
    assert not trees.status_data


def test__create_trees_from_inventory_plugin_items_key_and_inventory_columns() -> None:
    trees = _create_trees_from_inventory_plugin_items(
        [
            ItemsOfInventoryPlugin(
                [
                    TableRow(
                        path=["path-to-node"],
                        key_columns={"kkey": "kvalue"},
                        inventory_columns={"ikey": "ivalue"},
                    )
                ],
                None,
            ),
        ]
    )
    assert trees.inventory
    assert not trees.status_data


def test__create_trees_from_inventory_plugin_items_key_and_status_columns() -> None:
    trees = _create_trees_from_inventory_plugin_items(
        [
            ItemsOfInventoryPlugin(
                [
                    TableRow(
                        path=["path-to-node"],
                        key_columns={"kkey": "kvalue"},
                        status_columns={"skey": "svalue"},
                    )
                ],
                None,
            ),
        ]
    )
    assert not trees.inventory
    assert trees.status_data


def test__create_trees_from_inventory_plugin_items() -> None:
    trees = _create_trees_from_inventory_plugin_items(
        [
            ItemsOfInventoryPlugin(
                [
                    TableRow(
                        path=["path-to-node"],
                        key_columns={"kkey": "kvalue"},
                        inventory_columns={"ikey": "ivalue"},
                        status_columns={"skey": "svalue"},
                    )
                ],
                None,
            ),
        ]
    )
    assert trees.inventory
    assert trees.status_data
