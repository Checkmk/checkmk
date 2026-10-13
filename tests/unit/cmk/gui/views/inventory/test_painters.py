#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.inventory.filters import FilterInvtableText
from cmk.gui.logged_in import user
from cmk.gui.painter import EmptyCell
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import CSVExportError
from cmk.gui.views.inventory import NodeDisplayHint
from cmk.gui.views.inventory._display_hints import (
    _wrap_paint_function,
    ColumnDisplayHintOfView,
    Table,
)
from cmk.gui.views.inventory._paint_functions import inv_paint_generic
from cmk.gui.views.inventory._painters import (
    _get_delta_tree,
    _get_inventory_tree,
    make_inventory_column_painter,
    make_inventory_node_painter,
)
from cmk.inventory.delta import ImmutableDeltaTree
from cmk.inventory.serialization import deserialize_tree
from cmk.inventory.trees import ImmutableTree, SDKey
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


def _tree() -> ImmutableTree:
    return deserialize_tree({"Attributes": {"Pairs": {SDKey("key"): "value"}}})


def test_get_inventory_tree_reads_the_column() -> None:
    assert _get_inventory_tree(Row({"host_inventory": _tree()})) == _tree()


def test_get_inventory_tree_without_the_column() -> None:
    assert _get_inventory_tree(Row({})) == ImmutableTree()


def test_get_inventory_tree_of_an_unusable_column() -> None:
    assert _get_inventory_tree(Row({"host_inventory": "not a tree"})) == ImmutableTree()


def test_get_delta_tree_without_the_column() -> None:
    assert _get_delta_tree(Row({})) == ImmutableDeltaTree()


def test_get_delta_tree_of_an_unusable_column() -> None:
    assert _get_delta_tree(Row({"invhist_delta": "not a tree"})) == ImmutableDeltaTree()


def _column_hint() -> ColumnDisplayHintOfView:
    return ColumnDisplayHintOfView(
        name="invtable_col",
        title="Col",
        short_title="Col",
        long_title="Table > Col",
        paint_function=_wrap_paint_function(inv_paint_generic),
        sort_function=lambda *args: 0,  # noqa: ARG005
        filter=FilterInvtableText(inv_info="invtable", ident="invtable_col", title="Col"),
    )


def _node_hint() -> NodeDisplayHint:
    return NodeDisplayHint(
        name="inv",
        path=(),
        title="Node",
        short_title="Node",
        long_title="Node",
        icon="",
        attributes={},
        table=Table(columns={}),
    )


def test_inventory_column_painter_exports_the_column_value_for_csv() -> None:
    painter = make_inventory_column_painter(_column_hint())
    context = make_painter_context(UserPermissions({}, {}, {}, []))
    assert painter.export_for_csv({"invtable_col": 42}, EmptyCell(), user, context) == "42"


def test_inventory_node_painter_cannot_be_exported_to_csv() -> None:
    painter = make_inventory_node_painter(_node_hint())
    context = make_painter_context(UserPermissions({}, {}, {}, []))
    with pytest.raises(CSVExportError):
        painter.export_for_csv({"host_inventory": _tree()}, EmptyCell(), user, context)
