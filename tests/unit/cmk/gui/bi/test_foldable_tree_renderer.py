#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.bi.foldable_tree_renderer import (
    FoldableTreeRendererBoxes,
    FoldableTreeRendererTree,
)
from cmk.gui.type_defs import Row
from tests.unit.cmk.gui.compare_html import click_handling, inline_event_handlers


def _state() -> dict[str, object]:
    return {
        "state": 0,
        "output": "",
        "in_downtime": 0,
        "acknowledged": False,
        "in_service_period": True,
    }


def _row() -> Row:
    leaf = (_state(), None, {"title": "CPU", "host": ("heute", "my\\host"), "service": "C\\PU"})
    return {
        "aggr_treestate": (_state(), None, {"title": "Aggregation"}, [leaf]),
        "aggr_hosts": [("heute", "my\\host")],
        "aggr_tree": {"title": "Aggregation", "aggregation_id": "aggr"},
        "aggr_group": "Group",
    }


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_tree_toggles_subtrees_and_assumptions_by_click_actions() -> None:
    code = FoldableTreeRendererTree(
        _row(),
        omit_root=False,
        expansion_level=1,
        only_diff=False,
        only_problems=False,
        lazy=True,
        escape_plugin_output=True,
    ).render()

    assert inline_event_handlers(code) == []
    assert click_handling(code, "img.treeangle") == (None, "bi_toggle_subtree", {"lazy": "false"})
    assert click_handling(code, "a.assumption") == (
        None,
        "bi_toggle_assumption",
        {"site": "heute", "host": "my\\host", "service": "C\\PU"},
    )


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_boxes_toggle_lazily_by_click_action() -> None:
    code = FoldableTreeRendererBoxes(
        _row(),
        omit_root=False,
        expansion_level=0,
        only_diff=False,
        only_problems=False,
        lazy=True,
        escape_plugin_output=True,
    ).render()

    assert inline_event_handlers(code) == []
    assert click_handling(code, "span.bibox_box.noleaf") == (
        None,
        "bi_toggle_box",
        {"lazy": "true"},
    )
