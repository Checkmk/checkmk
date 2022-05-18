#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Tuple

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
from cmk.gui.plugins.views.utils import inventory_displayhints
from cmk.gui.plugins.visuals.inventory import FilterInvtableVersion
from cmk.gui.views import View
from cmk.gui.views.inventory import (
    _cmp_inv_generic,
    AttributeDisplayHint,
    AttributesDisplayHint,
    ColumnDisplayHint,
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
                title="Inventory",
                short_title="Inventory",
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                raw_path=".hardware.",
                icon="hardware",
                title="Hardware",
                short_title="Hardware",
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                raw_path=".path.to.node.",
                icon=None,
                title="Node",
                short_title="Node",
            ),
        ),
    ],
)
def test_make_node_displayhint(node_path: SDPath, expected: NodeDisplayHint) -> None:
    assert NodeDisplayHint.make(node_path) == expected


@pytest.mark.parametrize(
    "raw_node_path, expected",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                raw_path=".foo.bar.",
                icon=None,
                title="Bar",
                short_title="Bar",
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                raw_path=".software.",
                icon="software",
                title="Software",
                short_title="Software",
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_node_path: SDRawPath, expected: NodeDisplayHint
) -> None:
    assert (
        NodeDisplayHint.make_from_hint(
            raw_node_path,
            inventory_displayhints.get(raw_node_path, {}),
        )
        == expected
    )


@pytest.mark.parametrize(
    "table_path, expected",
    [
        (
            tuple(),
            TableDisplayHint(
                raw_path=".",
                key_order=[],
                is_show_more=True,
                view_name=None,
                short_title="Inventory",
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            TableDisplayHint(
                raw_path=".software.applications.docker.images:",
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
                short_title="Images",
            ),
        ),
        (
            ("path", "to", "node"),
            TableDisplayHint(
                raw_path=".path.to.node:",
                key_order=[],
                is_show_more=True,
                view_name=None,
                short_title="Node",
            ),
        ),
    ],
)
def test_make_table_displayhint(table_path: SDPath, expected: TableDisplayHint) -> None:
    assert TableDisplayHint.make(table_path) == expected


@pytest.mark.parametrize(
    "raw_table_path, expected",
    [
        (
            ".foo.bar:",
            TableDisplayHint(
                raw_path=".foo.bar:",
                key_order=[],
                is_show_more=True,
                view_name=None,
                short_title="Bar",
            ),
        ),
        (
            ".software.applications.docker.containers:",
            TableDisplayHint(
                raw_path=".software.applications.docker.containers:",
                key_order=["id", "creation", "name", "labels", "status", "image"],
                is_show_more=False,
                view_name="invdockercontainers_of_host",
                short_title="Containers",
            ),
        ),
    ],
)
def test_make_table_displayhint_from_hint(
    raw_table_path: SDRawPath, expected: TableDisplayHint
) -> None:
    assert (
        TableDisplayHint.make_from_hint(
            raw_table_path,
            inventory_displayhints.get(raw_table_path, {}),
        )
        == expected
    )


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
    path = ["software", "applications", "oracle", "dataguard_stats"]
    table_hint = TableDisplayHint.make(path)
    assert table_hint.sort_rows(rows, table_hint.make_titles(rows, ["sid"], path)) == expected


@pytest.mark.parametrize(
    "col_path, key, expected",
    [
        (
            tuple(),
            "key",
            ColumnDisplayHint(
                raw_path=".",
                short_title="Key",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                sort_function=_cmp_inv_generic,
            ),
        ),
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHint(
                raw_path=".networking.interfaces:*.oper_status",
                short_title="Status",
                data_type="if_oper_status",
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                sort_function=_cmp_inv_generic,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                raw_path=".path.to.node:*.key",
                short_title="Key",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                sort_function=_cmp_inv_generic,
            ),
        ),
    ],
)
def test_make_column_displayhint(col_path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    assert ColumnDisplayHint.make(col_path, key) == expected


@pytest.mark.parametrize(
    "raw_col_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                raw_path=".foo:*.bar",
                short_title="Bar",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Bar",
                sort_function=_cmp_inv_generic,
            ),
        ),
        (
            ".software.packages:*.package_version",
            ColumnDisplayHint(
                raw_path=".software.packages:*.package_version",
                short_title="Package Version",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Package Version",
                sort_function=cmp_version,
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHint(
                raw_path=".networking.interfaces:*.index",
                short_title="Index",
                data_type="number",
                paint_function=inv_paint_number,
                title="Index",
                sort_function=_cmp_inv_generic,
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHint(
                raw_path=".networking.interfaces:*.oper_status",
                short_title="Status",
                data_type="if_oper_status",
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                sort_function=_cmp_inv_generic,
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(
    raw_col_path: SDRawPath, expected: ColumnDisplayHint
) -> None:
    assert (
        ColumnDisplayHint.make_from_hint(
            raw_col_path,
            inventory_displayhints.get(raw_col_path, {}),
        )
        == expected
    )


@pytest.mark.parametrize(
    "attrs_path, expected",
    [
        (
            tuple(),
            AttributesDisplayHint(
                key_order=[],
            ),
        ),
        (
            ("hardware", "cpu"),
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
        ),
        (
            ("path", "to", "node"),
            AttributesDisplayHint(
                key_order=[],
            ),
        ),
    ],
)
def test_make_attributes_displayhint(attrs_path: SDPath, expected: AttributesDisplayHint) -> None:
    assert AttributesDisplayHint.make(attrs_path) == expected


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
    attrs_hint = AttributesDisplayHint.make(["software", "applications", "kube", "metadata"])
    assert attrs_hint.sort_pairs(pairs) == expected


@pytest.mark.parametrize(
    "attr_path, key, expected",
    [
        (
            tuple(),
            "key",
            AttributeDisplayHint(
                raw_path=".",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                short_title="Key",
                is_show_more=True,
            ),
        ),
        (
            ("hardware", "storage", "disks"),
            "size",
            AttributeDisplayHint(
                raw_path=".hardware.storage.disks.size",
                data_type="size",
                paint_function=inv_paint_size,
                title="Size",
                short_title="Size",
                is_show_more=True,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                raw_path=".path.to.node.key",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Key",
                short_title="Key",
                is_show_more=True,
            ),
        ),
    ],
)
def test_make_attribute_displayhint(
    attr_path: SDPath, key: str, expected: AttributeDisplayHint
) -> None:
    assert AttributeDisplayHint.make(attr_path, key) == expected


@pytest.mark.parametrize(
    "raw_attr_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                raw_path=".foo.bar",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Bar",
                short_title="Bar",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                raw_path=".hardware.cpu.arch",
                data_type="str",
                paint_function=inv_paint_generic,
                title="CPU Architecture",
                short_title="CPU Arch",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                raw_path=".hardware.system.product",
                data_type="str",
                paint_function=inv_paint_generic,
                title="Product",
                short_title="Product",
                is_show_more=False,
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_attr_path: SDRawPath, expected: AttributeDisplayHint
) -> None:
    assert (
        AttributeDisplayHint.make_from_hint(
            raw_attr_path,
            inventory_displayhints.get(raw_attr_path, {}),
        )
        == expected
    )
