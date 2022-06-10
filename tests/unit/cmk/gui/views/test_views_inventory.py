#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Tuple

# No stub file
import pytest

from cmk.utils.structured_data import (
    SDKey,
    SDPairs,
    SDPath,
    SDRawPath,
    SDRow,
    SDValue,
    StructuredDataNode,
)

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.num_split import cmp_version
from cmk.gui.plugins.visuals.inventory import FilterInvtableVersion
from cmk.gui.views import View
from cmk.gui.views.inventory import (
    _cmp_inv_generic,
    AttributeDisplayHint,
    AttributesDisplayHint,
    ColumnDisplayHint,
    DISPLAY_HINTS,
    inv_paint_generic,
    inv_paint_if_oper_status,
    inv_paint_number,
    inv_paint_size,
    NodeDisplayHint,
    RowTableInventory,
    RowTableInventoryHistory,
    TableDisplayHint,
)

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
    row_table = RowTableInventory(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view, [], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_unknown_columns(monkeypatch):
    row_table = RowTableInventory(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view, ["foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_add_columns(monkeypatch):
    row_table = RowTableInventory(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
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
    sources = list(
        zip(
            ["invtesttable1", "invtesttable2"],
            [
                cmk.gui.inventory.InventoryPath.parse(".foo.bar:"),
                cmk.gui.inventory.InventoryPath.parse("foo.baz:"),
            ],
        )
    )
    row_table = cmk.gui.views.inventory.RowMultiTableInventory(sources, ["sid"], [])
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS_MULTI)
    rows, _len_rows = row_table.query(view, [], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_MULTI_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_multi_table_inventory_unknown_columns(monkeypatch):
    sources = list(
        zip(
            ["invtesttable1", "invtesttable2"],
            [
                cmk.gui.inventory.InventoryPath.parse(".foo.bar:"),
                cmk.gui.inventory.InventoryPath.parse("foo.baz:"),
            ],
        )
    )
    row_table = cmk.gui.views.inventory.RowMultiTableInventory(sources, ["sid"], [])
    view = View("", {}, {})
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS_MULTI)
    rows, _len_rows = row_table.query(view, ["foo"], "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_MULTI_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_multi_table_inventory_add_columns(monkeypatch):
    sources = list(
        zip(
            ["invtesttable1", "invtesttable2"],
            [
                cmk.gui.inventory.InventoryPath.parse(".foo.bar:"),
                cmk.gui.inventory.InventoryPath.parse("foo.baz:"),
            ],
        )
    )
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
    monkeypatch.setattr(cmk.gui.inventory, "get_attribute", lambda val, path: val)
    assert (
        cmk.gui.views.inventory._cmp_inventory_node(
            {"host_inventory": val_a},
            {"host_inventory": val_b},
            cmk.gui.inventory.InventoryPath.parse(".any.path"),
        )
        == result
    )


@pytest.mark.parametrize(
    "path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            tuple(),
            NodeDisplayHint(
                icon=None,
                title="Inventory",
                short_title="Inventory",
                _long_title_function=lambda: "Inventory",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                icon="hardware",
                title="Hardware",
                short_title="Hardware",
                _long_title_function=lambda: "Hardware",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
        (
            ("hardware", "cpu"),
            NodeDisplayHint(
                icon=None,
                title="Processor",
                short_title="Processor",
                _long_title_function=lambda: "Hardware ➤ Processor",
            ),
            AttributesDisplayHint(
                key_order=[
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
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            NodeDisplayHint(
                icon=None,
                title="Images",
                short_title="Images",
                _long_title_function=lambda: "Docker ➤ Images",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[
                    "id",
                    "creation",
                    "size",
                    "labels",
                    "amount_containers",
                    "repotags",
                    "repodigests",
                ],
                is_show_more=False,
                view_name="invdockerimages_of_host",
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                icon=None,
                title="Node",
                short_title="Node",
                _long_title_function=lambda: "To ➤ Node",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
    ],
)
def test_make_node_displayhint(
    path: SDPath,
    expected_node_hint: NodeDisplayHint,
    expected_attributes_hint: AttributesDisplayHint,
    expected_table_hint: TableDisplayHint,
) -> None:
    hints = DISPLAY_HINTS.get_hints(path)

    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.short_title == expected_node_hint.short_title
    assert hints.node_hint.long_title == expected_node_hint.long_title

    assert hints.attributes_hint.key_order == expected_attributes_hint.key_order

    assert hints.table_hint.key_order == expected_table_hint.key_order
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more
    assert hints.table_hint.view_name == expected_table_hint.view_name


@pytest.mark.parametrize(
    "raw_path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                icon=None,
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                icon=None,
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                icon="software",
                title="Software",
                short_title="Software",
                _long_title_function=lambda: "Software",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_name=None,
            ),
        ),
        (
            ".software.applications.docker.containers:",
            NodeDisplayHint(
                icon=None,
                title="Containers",
                short_title="Containers",
                _long_title_function=lambda: "Docker ➤ Containers",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=["id", "creation", "name", "labels", "status", "image"],
                is_show_more=False,
                view_name="invdockercontainers_of_host",
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_path: SDRawPath,
    expected_node_hint: NodeDisplayHint,
    expected_attributes_hint: AttributesDisplayHint,
    expected_table_hint: TableDisplayHint,
) -> None:
    hints = DISPLAY_HINTS.get_hints(cmk.gui.inventory.InventoryPath.parse(raw_path).path)

    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.short_title == expected_node_hint.short_title
    assert hints.node_hint.long_title == expected_node_hint.long_title

    assert hints.attributes_hint.key_order == expected_attributes_hint.key_order

    assert hints.table_hint.key_order == expected_table_hint.key_order
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more
    assert hints.table_hint.view_name == expected_table_hint.view_name


@pytest.mark.parametrize(
    "rows, expected",
    [
        ([], []),
        ([{}], [{}]),
        (
            [
                {"sid": "SID 2", "flashback": "Flashback 2", "other": "Other 2"},
                {"sid": "SID 1", "flashback": "Flashback 1", "other": "Other 1"},
            ],
            [
                {"flashback": "Flashback 1", "other": "Other 1", "sid": "SID 1"},
                {"flashback": "Flashback 2", "other": "Other 2", "sid": "SID 2"},
            ],
        ),
    ],
)
def test_sort_table_rows_displayhint(rows: Sequence[SDRow], expected: Sequence[SDRow]) -> None:
    raw_path = ".software.applications.oracle.dataguard_stats:"
    path = cmk.gui.inventory.InventoryPath.parse(raw_path).path
    table_hint = DISPLAY_HINTS.get_hints(path).table_hint
    assert (
        table_hint.sort_rows(
            rows,
            table_hint.make_columns(rows, ["sid"], path),
        )
        == expected
    )


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            ColumnDisplayHint(
                short_title="Key",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                sort_function=_cmp_inv_generic,
                filter_class=None,
            ),
        ),
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHint(
                short_title="Status",
                data_type="if_oper_status",
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                sort_function=_cmp_inv_generic,
                filter_class=None,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                short_title="Key",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                sort_function=_cmp_inv_generic,
                filter_class=None,
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_hints(path).get_column_hint(key)

    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.data_type == expected.data_type
    assert hint.paint_function == expected.paint_function
    assert hint.sort_function == expected.sort_function


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                short_title="Bar",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Bar",
                sort_function=_cmp_inv_generic,
                filter_class=None,
            ),
        ),
        (
            ".software.packages:*.package_version",
            ColumnDisplayHint(
                short_title="Package Version",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Package Version",
                sort_function=cmp_version,
                filter_class=None,
            ),
        ),
        (
            ".software.packages:*.version",
            ColumnDisplayHint(
                short_title="Version",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Version",
                sort_function=cmp_version,
                filter_class=FilterInvtableVersion,
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHint(
                short_title="Index",
                data_type="number",
                paint_function=inv_paint_number,
                title="Index",
                sort_function=_cmp_inv_generic,
                filter_class=None,
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHint(
                short_title="Status",
                data_type="if_oper_status",
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                sort_function=_cmp_inv_generic,
                filter_class=None,
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(
    raw_path: SDRawPath, expected: ColumnDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.InventoryPath.parse(raw_path)
    hint = DISPLAY_HINTS.get_hints(inventory_path.path).get_column_hint(inventory_path.key or "")

    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.data_type == expected.data_type
    assert hint.paint_function == expected.paint_function
    assert hint.sort_function == expected.sort_function


@pytest.mark.parametrize(
    "pairs, expected",
    [
        ({}, []),
        (
            {"namespace": "Namespace", "name": "Name", "object": "Object", "other": "Other"},
            [
                ("object", "Object"),
                ("name", "Name"),
                ("namespace", "Namespace"),
                ("other", "Other"),
            ],
        ),
    ],
)
def test_sort_attributes_pairs_displayhint(
    pairs: SDPairs, expected: Sequence[Tuple[SDKey, SDValue]]
) -> None:
    raw_path = ".software.applications.kube.metadata."
    path = cmk.gui.inventory.InventoryPath.parse(raw_path).path
    attrs_hint = DISPLAY_HINTS.get_hints(path).attributes_hint
    assert attrs_hint.sort_pairs(pairs) == expected


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                short_title="Key",
                _long_title_function=lambda: "Key",
                is_show_more=True,
            ),
        ),
        (
            ("hardware", "storage", "disks"),
            "size",
            AttributeDisplayHint(
                data_type="size",
                paint_function=inv_paint_size,
                title="Size",
                short_title="Size",
                _long_title_function=lambda: "Block Devices ➤ Size",
                is_show_more=True,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                short_title="Key",
                _long_title_function=lambda: "Node ➤ Key",
                is_show_more=True,
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_hints(path).get_attribute_hint(key)

    assert hint.data_type == expected.data_type
    assert hint.paint_function == expected.paint_function
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert hint.is_show_more == expected.is_show_more


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                title="Bar",
                short_title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                title="CPU Architecture",
                short_title="CPU Arch",
                _long_title_function=lambda: "Processor ➤ CPU Architecture",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                title="Product",
                short_title="Product",
                _long_title_function=lambda: "System ➤ Product",
                is_show_more=False,
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_path: SDRawPath, expected: AttributeDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.InventoryPath.parse(raw_path)
    hint = DISPLAY_HINTS.get_hints(inventory_path.path).get_attribute_hint(inventory_path.key or "")

    assert hint.data_type == expected.data_type
    assert hint.paint_function == expected.paint_function
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert hint.is_show_more == expected.is_show_more


@pytest.mark.parametrize(
    "abc_path, path, expected_title",
    [
        (
            ("software", "applications", "vmwareesx", "*"),
            ("software", "applications", "vmwareesx", "1"),
            "Datacenter 1",
        ),
        (
            ("software", "applications", "vmwareesx", "*", "clusters", "*"),
            ("software", "applications", "vmwareesx", "1", "clusters", "2"),
            "Cluster 2",
        ),
    ],
)
def test_replace_placeholder(abc_path: SDPath, path: SDPath, expected_title: str) -> None:
    assert DISPLAY_HINTS.get_hints(abc_path).replace_placeholders(path) == expected_title
