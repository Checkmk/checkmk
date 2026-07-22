#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.inventory._tree import InventoryPath, TreeSource
from cmk.gui.inventory.filters import FilterInvBool, FilterInvFloat, FilterInvFloatChoice
from cmk.gui.type_defs import Rows, VisualContext
from cmk.inventory.structured_data import (
    ImmutableAttributes,
    ImmutableTree,
    SDKey,
    SDNodeName,
    SDValue,
)


def _make_host_inventory_tree(value: SDValue) -> ImmutableTree:
    return ImmutableTree(
        nodes_by_name={
            SDNodeName("path-to-node"): ImmutableTree(
                attributes=ImmutableAttributes(pairs={SDKey("key"): value})
            )
        }
    )


@pytest.mark.parametrize(
    "context, rows, expected_rows",
    [
        pytest.param(
            {},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            id="no-context",
        ),
        pytest.param(
            {"ident": {}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            id="no-http-filter-vars",
        ),
        pytest.param(
            {"ident": {"ident_from": "2"}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            id="from",
        ),
        pytest.param(
            {"ident": {"ident_until": "2"}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
            ],
            id="until",
        ),
        pytest.param(
            {"ident": {"ident_from": "2", "ident_until": "4"}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
                {"host_inventory": _make_host_inventory_tree(4)},
                {"host_inventory": _make_host_inventory_tree(5)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
                {"host_inventory": _make_host_inventory_tree(4)},
            ],
            id="from-until",
        ),
    ],
)
def test_filter_inv_float(context: VisualContext, rows: Rows, expected_rows: Rows) -> None:
    assert (
        FilterInvFloat(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
            unit_choices={},
        ).filter_table(context, rows)
        == expected_rows
    )


@pytest.mark.parametrize(
    "context, rows, expected_rows",
    [
        pytest.param(
            {"ident": {"ident_from": "2", "ident_from_prefix": "k"}},
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
            ],
            id="from",
        ),
        pytest.param(
            {"ident": {"ident_until": "2", "ident_until_prefix": "k"}},
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
            ],
            id="until",
        ),
        pytest.param(
            {
                "ident": {
                    "ident_from": "2",
                    "ident_from_prefix": "k",
                    "ident_until": "4",
                    "ident_until_prefix": "M",
                }
            },
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
                {"host_inventory": _make_host_inventory_tree(400)},
                {"host_inventory": _make_host_inventory_tree(500)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
                {"host_inventory": _make_host_inventory_tree(400)},
            ],
            id="from-until",
        ),
    ],
)
def test_filter_inv_float_unit_choices(
    context: VisualContext, rows: Rows, expected_rows: Rows
) -> None:
    assert (
        FilterInvFloat(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
            unit_choices={
                "": FilterInvFloatChoice("U", 1),
                "k": FilterInvFloatChoice("kU", 10),
                "M": FilterInvFloatChoice("MU", 100),
            },
        ).filter_table(context, rows)
        == expected_rows
    )


@pytest.mark.parametrize(
    "context, rows, expected_rows",
    [
        pytest.param(
            {},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            id="no-context",
        ),
        pytest.param(
            {"ident": {"is_ident": "-1"}},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            id="ignore",
        ),
        pytest.param(
            {"ident": {"is_ident": "1"}},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(True)},
            ],
            id="select-true",
        ),
        pytest.param(
            {"ident": {"is_ident": "0"}},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            id="select-false",
        ),
    ],
)
def test_filter_inv_bool(context: VisualContext, rows: Rows, expected_rows: Rows) -> None:
    assert (
        FilterInvBool(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
        ).filter_table(context, rows)
        == expected_rows
    )
