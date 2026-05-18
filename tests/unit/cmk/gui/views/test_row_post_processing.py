#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.type_defs import Rows
from cmk.gui.view import View
from cmk.gui.views.inventory._row_post_processor import _add_inventory_data
from cmk.gui.views.row_post_processing import post_process_rows, row_post_processor_registry
from cmk.inventory.structured_data import ImmutableTree


def test_post_processor_registrations() -> None:
    names = [f.__name__ for f in row_post_processor_registry.values()]
    expected = [
        "inventory_row_post_processor",
        "join_service_row_post_processor",
    ]
    assert sorted(names) == sorted(expected)


def test_post_process_rows_not_failing_on_empty_rows(view: View) -> None:
    rows: Rows = []
    post_process_rows(view, [], rows)
    assert not rows


def test_add_inventory_data_attaches_immutable_tree_to_rows(request_context: None) -> None:
    """`_add_inventory_data` loads the inventory tree for each row and stores
    it under `host_inventory`. The tree itself comes from `load_tree`, which
    returns an empty `ImmutableTree` when the host has no on-disk inventory —
    that's the case here, since the test doesn't materialise any host files.
    What we're asserting is the post-processor's contract: every row that
    carries a `host_name` ends up with a `host_inventory` of type
    `ImmutableTree`, regardless of which view triggered the post-processing.
    """
    host_row: dict[str, object] = {"site": "ding", "host_name": "dong"}
    rows: Rows = [host_row]
    _add_inventory_data(rows)
    assert rows == [host_row]
    assert isinstance(host_row["host_inventory"], ImmutableTree)
