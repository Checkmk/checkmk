#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

# No stub file
import pytest

from cmk.utils.structured_data import SDPath, StructuredDataNode

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.num_split import cmp_version
from cmk.gui.plugins.visuals.inventory import FilterInvtableVersion
from cmk.gui.views import View
from cmk.gui.views.inventory import NodeDisplayHint, RowTableInventory, RowTableInventoryHistory

RAW_ROWS = [("this_site", "this_hostname")]
RAW_ROWS2 = [("this_site", "this_hostname", "foobar")]

INV_ROWS = [
    {"sid": "A", "value1": 1, "value2": 4},
    {"sid": "B", "value1": 2, "value2": 5},
    {"sid": "C", "value1": 3, "value2": 6},
]

EXPECTED_INV_KEYS = [
    "site",
    "host_name",
    "invtesttable_sid",
    "invtesttable_value1",
    "invtesttable_value2",
]

INV_HIST_ROWS = [
    cmk.gui.inventory.HistoryEntry(123, 1, 2, 3, StructuredDataNode()),
    cmk.gui.inventory.HistoryEntry(456, 4, 5, 6, StructuredDataNode()),
    cmk.gui.inventory.HistoryEntry(789, 7, 8, 9, StructuredDataNode()),
]

EXPECTED_INV_HIST_KEYS = [
    "site",
    "host_name",
    "invhist_time",
    "invhist_delta",
    "invhist_removed",
    "invhist_new",
    "invhist_changed",
]

INV_ROWS_MULTI = [
    (
        "invtesttable1",
        [
            {
                "sid": "A",
                "value1": 1,
            },
            {
                "sid": "B",
                "value1": 2,
            },
            {
                "sid": "C",
                "value1": 3,
            },
        ],
    ),
    (
        "invtesttable2",
        [
            {
                "sid": "A",
                "value2": 4,
            },
            {
                "sid": "B",
                "value2": 5,
            },
            {
                "sid": "C",
                "value2": 6,
            },
        ],
    ),
]

EXPECTED_INV_MULTI_KEYS = [
    "site",
    "host_name",
    "invtesttable1_sid",
    "invtesttable1_value1",
    "invtesttable2_sid",
    "invtesttable2_value2",
]


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory(monkeypatch):
    row_table = RowTableInventory("invtesttable", ".foo.bar:")
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view, [], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_unknown_columns(monkeypatch):
    row_table = RowTableInventory("invtesttable", ".foo.bar:")
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view, ["foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_add_columns(monkeypatch):
    row_table = RowTableInventory("invtesttable", ".foo.bar:")
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view, ["host_foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS + ["host_foo"])


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history(monkeypatch):
    row_table = RowTableInventoryHistory()
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows, _len_rows = row_table.query(view, [], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history_unknown_columns(monkeypatch):
    row_table = RowTableInventoryHistory()
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows, _len_rows = row_table.query(view, ["foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history_add_columns(monkeypatch):
    row_table = RowTableInventoryHistory()
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows, _len_rows = row_table.query(view, ["host_foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS + ["host_foo"])


@pytest.mark.usefixtures("request_context")
def test_query_row_multi_table_inventory(monkeypatch):
    sources = list(zip(["invtesttable1", "invtesttable2"], [".foo.bar:", "foo.baz:"]))
    row_table = cmk.gui.views.inventory.RowMultiTableInventory(sources, ["sid"], [])
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS_MULTI)
    rows, _len_rows = row_table.query(view, [], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_MULTI_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_multi_table_inventory_unknown_columns(monkeypatch):
    sources = list(zip(["invtesttable1", "invtesttable2"], [".foo.bar:", "foo.baz:"]))
    row_table = cmk.gui.views.inventory.RowMultiTableInventory(sources, ["sid"], [])
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS_MULTI)
    rows, _len_rows = row_table.query(view, ["foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_MULTI_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_multi_table_inventory_add_columns(monkeypatch):
    sources = list(zip(["invtesttable1", "invtesttable2"], [".foo.bar:", "foo.baz:"]))
    row_table = cmk.gui.views.inventory.RowMultiTableInventory(sources, ["sid"], [])
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS_MULTI)
    rows, _len_rows = row_table.query(view, ["host_foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_MULTI_KEYS + ["host_foo"])


@pytest.mark.parametrize(
    "val_a, val_b, result",
    [
        (None, None, 0),
        (None, 0, -1),
        (0, None, 1),
        (0, 0, 0),
        (1, 0, 1),
        (0, 1, -1),
    ],
)
def test__cmp_inventory_node(monkeypatch, val_a, val_b, result):
    monkeypatch.setattr(cmk.gui.inventory, "get_inventory_attribute", lambda val, path: val)
    assert (
        cmk.gui.views.inventory._cmp_inventory_node(
            {"host_inventory": val_a}, {"host_inventory": val_b}, "any-path"
        )
        == result
    )


@pytest.mark.parametrize(
    "invpath, expected_hint",
    [
        # root
        (
            "",
            {
                "title": "Inventory",
            },
        ),
        (
            ".",
            {
                "title": "Inventory",
            },
        ),
        # 'short'
        (
            ".hardware.cpu.arch",
            {
                "title": "CPU Architecture",
                "short": "CPU Arch",
            },
        ),
        # 'keyorder'
        (
            ".hardware.cpu.",
            {
                "title": "Processor",
                "keyorder": [
                    "arch",
                    "max_speed",
                    "model",
                    "type",
                    "threads",
                    "smt_threads",
                    "sharing_mode",
                    "implementation_mode",
                    "entitlement",
                    "cpu_max_capa",
                    "logical_cpus",
                ],
            },
        ),
        # 'paint'
        (
            ".hardware.cpu.max_speed",
            {
                "title": "Maximum Speed",
                "paint": "hz",
                "paint_function": cmk.gui.views.inventory.inv_paint_hz,
            },
        ),
        # 'is_show_more'
        (
            ".hardware.system.product",
            {
                "title": "Product",
                "is_show_more": False,
            },
        ),
        # 'view'
        (
            ".hardware.components.others:",
            {
                "title": "Other entities",
                "keyorder": [
                    "index",
                    "name",
                    "description",
                    "software",
                    "serial",
                    "manufacturer",
                    "model",
                    "location",
                ],
                "view": "invother_of_host",
            },
        ),
        # 'icon'
        (
            ".software.packages:",
            {
                "title": "Packages",
                "icon": "packages",
                "keyorder": ["name", "version", "arch", "package_type", "summary"],
                "view": "invswpac_of_host",
                "is_show_more": False,
            },
        ),
        # 'sort', 'filter'
        (
            ".software.packages:*.version",
            {
                "title": "Version",
                "sort": cmp_version,
                "filter": FilterInvtableVersion,
            },
        ),
        # table headers
        (
            ".hardware.components.others:0.index",
            {
                "title": "Index",
            },
        ),
        # unknown
        (".path.to.something.", {}),
        (".path.to.something", {}),
        (".path.to.something:", {}),
    ],
)
def test__get_display_hint(invpath: str, expected_hint: Mapping[str, Any]) -> None:
    assert cmk.gui.views.inventory._get_display_hint(invpath) == expected_hint


@pytest.mark.parametrize(
    "node_path, expected",
    [
        (
            tuple(),
            NodeDisplayHint(
                raw_path=".",
                icon=None,
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                raw_path=".hardware.",
                icon="hardware",
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                raw_path=".path.to.node.",
                icon=None,
            ),
        ),
    ],
)
def test_make_node_displayhint(node_path: SDPath, expected: NodeDisplayHint):
    assert NodeDisplayHint.make(node_path) == expected
