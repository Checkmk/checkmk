#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

# No stub file
import pytest

from cmk.utils.structured_data import (
    ImmutableDeltaTree,
    ImmutableTree,
    RetentionInterval,
    SDKey,
    SDPath,
    SDValue,
)

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.num_split import cmp_version
from cmk.gui.painter.v0.base import JoinCell
from cmk.gui.plugins.visuals.inventory import FilterInvtableVersion
from cmk.gui.type_defs import ColumnSpec, PainterParameters
from cmk.gui.view import View
from cmk.gui.views.inventory import (
    _cmp_inv_generic,
    _decorate_sort_function,
    _DeltaRowOrRetentions,
    _register_sorter,
    _RowOrRetentions,
    _sort_pairs,
    _sort_rows,
    AttributeDisplayHint,
    AttributesDisplayHint,
    ColumnDisplayHint,
    DISPLAY_HINTS,
    inv_paint_generic,
    inv_paint_if_oper_status,
    inv_paint_number,
    inv_paint_service_status,
    inv_paint_size,
    NodeDisplayHint,
    RowTableInventory,
    RowTableInventoryHistory,
    TableDisplayHint,
    TableViewSpec,
)
from cmk.gui.views.inventory.row_post_processor import _join_inventory_rows
from cmk.gui.views.sorter import sorter_registry
from cmk.gui.views.store import multisite_builtin_views

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
    cmk.gui.inventory.HistoryEntry(123, 1, 2, 3, ImmutableDeltaTree()),
    cmk.gui.inventory.HistoryEntry(456, 4, 5, 6, ImmutableDeltaTree()),
    cmk.gui.inventory.HistoryEntry(789, 7, 8, 9, ImmutableDeltaTree()),
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


@pytest.fixture(name="view")
def fixture_view() -> View:
    """Provide some arbitrary view for testing"""
    view_spec = multisite_builtin_views["invinterface_of_host"]
    return View("invdockerimages", view_spec, view_spec["context"])


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory(monkeypatch: pytest.MonkeyPatch, view: View) -> None:
    row_table = RowTableInventory(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view.datasource, [], [], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_unknown_columns(
    monkeypatch: pytest.MonkeyPatch, view: View
) -> None:
    row_table = RowTableInventory(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view.datasource, [], ["foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_add_columns(monkeypatch: pytest.MonkeyPatch, view: View) -> None:
    row_table = RowTableInventory(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows, _len_rows = row_table.query(view.datasource, [], ["host_foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS + ["host_foo"])


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history(monkeypatch: pytest.MonkeyPatch, view: View) -> None:
    row_table = RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows, _len_rows = row_table.query(view.datasource, [], [], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history_unknown_columns(
    monkeypatch: pytest.MonkeyPatch, view: View
) -> None:
    row_table = RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows, _len_rows = row_table.query(view.datasource, [], ["foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history_add_columns(
    monkeypatch: pytest.MonkeyPatch, view: View
) -> None:
    row_table = RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows, _len_rows = row_table.query(view.datasource, [], ["host_foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS + ["host_foo"])


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
def test__cmp_inv_generic(val_a: object, val_b: object, result: int) -> None:
    assert _decorate_sort_function(_cmp_inv_generic)(val_a, val_b) == result


@pytest.mark.parametrize(
    "path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            tuple(),
            NodeDisplayHint(
                icon=None,
                title="Inventory Tree",
                _long_title_function=lambda: "Inventory Tree",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                icon="hardware",
                title="Hardware",
                _long_title_function=lambda: "Hardware",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ("hardware", "cpu"),
            NodeDisplayHint(
                icon=None,
                title="Processor",
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
                    "cpu_max_capa",
                    "cpus",
                    "logical_cpus",
                    "cores",
                    "cores_per_cpu",
                    "threads_per_cpu",
                    "cache_size",
                    "bus_speed",
                    "voltage",
                    "sharing_mode",
                    "implementation_mode",
                    "entitlement",
                ],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            NodeDisplayHint(
                icon=None,
                title="Docker images",
                _long_title_function=lambda: "Docker ➤ Docker images",
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
                view_spec=TableViewSpec(
                    view_name="invdockerimages",
                    title="Docker images",
                    _long_title_function=lambda: "Docker ➤ Docker images",
                    icon=None,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                icon=None,
                title="Node",
                _long_title_function=lambda: "To ➤ Node",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
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
    assert hints.node_hint.long_title == expected_node_hint.long_title
    assert hints.node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert hints.attributes_hint.key_order == expected_attributes_hint.key_order

    assert hints.table_hint.key_order == expected_table_hint.key_order
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more

    if expected_table_hint.view_spec:
        assert hints.table_hint.view_spec is not None
        assert hints.table_hint.view_spec.long_title == expected_table_hint.view_spec.long_title
        assert (
            hints.table_hint.view_spec.long_inventory_title
            == expected_table_hint.view_spec.long_inventory_title
        )


@pytest.mark.parametrize(
    "raw_path, expected_node_hint, expected_attributes_hint, expected_table_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                icon=None,
                title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                icon=None,
                title="Bar",
                _long_title_function=lambda: "Foo ➤ Bar",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                icon="software",
                title="Software",
                _long_title_function=lambda: "Software",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=[],
                is_show_more=True,
                view_spec=None,
            ),
        ),
        (
            ".software.applications.docker.containers:",
            NodeDisplayHint(
                icon=None,
                title="Docker containers",
                _long_title_function=lambda: "Docker ➤ Docker containers",
            ),
            AttributesDisplayHint(
                key_order=[],
            ),
            TableDisplayHint(
                key_order=["id", "creation", "name", "labels", "status", "image"],
                is_show_more=False,
                view_spec=TableViewSpec(
                    view_name="invdockercontainers",
                    title="Docker containers",
                    _long_title_function=lambda: "Docker ➤ Docker containers",
                    icon=None,
                ),
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_path: str,
    expected_node_hint: NodeDisplayHint,
    expected_attributes_hint: AttributesDisplayHint,
    expected_table_hint: TableDisplayHint,
) -> None:
    hints = DISPLAY_HINTS.get_hints(cmk.gui.inventory.InventoryPath.parse(raw_path).path)

    assert hints.node_hint.icon == expected_node_hint.icon
    assert hints.node_hint.title == expected_node_hint.title
    assert hints.node_hint.long_title == expected_node_hint.long_title
    assert hints.node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert hints.attributes_hint.key_order == expected_attributes_hint.key_order

    assert hints.table_hint.key_order == expected_table_hint.key_order
    assert hints.table_hint.is_show_more == expected_table_hint.is_show_more

    if expected_table_hint.view_spec:
        assert hints.table_hint.view_spec is not None
        assert hints.table_hint.view_spec.long_title == expected_table_hint.view_spec.long_title
        assert (
            hints.table_hint.view_spec.long_inventory_title
            == expected_table_hint.view_spec.long_inventory_title
        )


@pytest.mark.parametrize(
    "rows, expected",
    [
        ([], []),
        (
            [
                _RowOrRetentions(
                    {"sid": "SID 2", "flashback": "Flashback 2", "other": "Other 2"},
                    {"sid": RetentionInterval(1, 2, 3)},
                ),
                _RowOrRetentions(
                    {"sid": "SID 1", "flashback": "Flashback 1", "other": "Other 1"},
                    {},
                ),
                _RowOrRetentions(
                    {"sid": None, "flashback": None, "other": None},
                    {},
                ),
            ],
            [
                [
                    ("sid", "SID 1", None),
                    ("changed", None, None),
                    ("foo", None, None),
                    ("flashback", "Flashback 1", None),
                    ("other", "Other 1", None),
                ],
                [
                    ("sid", "SID 2", 6),
                    ("changed", None, None),
                    ("foo", None, None),
                    ("flashback", "Flashback 2", None),
                    ("other", "Other 2", None),
                ],
            ],
        ),
    ],
)
def test_sort_table_rows_displayhint(
    rows: Sequence[_RowOrRetentions],
    expected: Sequence[Sequence[tuple[SDKey, SDValue, RetentionInterval | None]]],
) -> None:
    assert _sort_rows(rows, ["sid", "changed", "foo", "flashback", "other"]) == expected


@pytest.mark.parametrize(
    "rows, expected",
    [
        ([], []),
        (
            [
                _DeltaRowOrRetentions(
                    {
                        "sid": ("SID 2", None),
                        "flashback": (None, "Flashback 2"),
                        "other": ("Other 2", "Other 2"),
                        "changed": ("Changed 21", "Changed 22"),
                    }
                ),
                _DeltaRowOrRetentions(
                    {
                        "sid": ("SID 1", None),
                        "flashback": (None, "Flashback 1"),
                        "other": ("Other 1", "Other 1"),
                        "changed": ("Changed 11", "Changed 12"),
                    }
                ),
                _DeltaRowOrRetentions(
                    {
                        "sid": ("SID 3", "SID 3"),
                        "flashback": ("Flashback 3", "Flashback 3"),
                        "other": (None, None),
                        "changed": (None, None),
                    }
                ),
            ],
            [
                [
                    ("sid", ("SID 1", None), None),
                    ("changed", ("Changed 11", "Changed 12"), None),
                    ("foo", None, None),
                    ("flashback", (None, "Flashback 1"), None),
                    ("other", ("Other 1", "Other 1"), None),
                ],
                [
                    ("sid", ("SID 2", None), None),
                    ("changed", ("Changed 21", "Changed 22"), None),
                    ("foo", None, None),
                    ("flashback", (None, "Flashback 2"), None),
                    ("other", ("Other 2", "Other 2"), None),
                ],
            ],
        ),
    ],
)
def test_sort_deltatable_rows_displayhint(
    rows: Sequence[_DeltaRowOrRetentions],
    expected: Sequence[Sequence[tuple[SDKey, tuple[SDValue, SDValue], None]]],
) -> None:
    assert _sort_rows(rows, ["sid", "changed", "foo", "flashback", "other"]) == expected


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Key",
                short=None,
                _long_title_function=lambda: "Key",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHint(
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                short=None,
                _long_title_function=lambda: "Network interfaces ➤ Operational Status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Key",
                short=None,
                _long_title_function=lambda: "Node ➤ Key",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
        (
            ("software", "applications", "check_mk", "sites"),
            "cmc",
            ColumnDisplayHint(
                paint_function=inv_paint_service_status,
                title="CMC status",
                short="CMC",
                _long_title_function=lambda: "Checkmk sites ➤ CMC status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_hints(path).get_column_hint(key)

    assert hint.title == expected.title
    assert hint.short == expected.short
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Bar",
                short=None,
                _long_title_function=lambda: "Foo ➤ Bar",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
        (
            ".software.packages:*.package_version",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Package Version",
                short=None,
                _long_title_function=lambda: "Software packages ➤ Package Version",
                sort_function=_decorate_sort_function(cmp_version),
                filter_class=None,
            ),
        ),
        (
            ".software.packages:*.version",
            ColumnDisplayHint(
                paint_function=inv_paint_generic,
                title="Version",
                short=None,
                _long_title_function=lambda: "Software packages ➤ Version",
                sort_function=_decorate_sort_function(cmp_version),
                filter_class=FilterInvtableVersion,
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHint(
                paint_function=inv_paint_number,
                title="Index",
                short=None,
                _long_title_function=lambda: "Network interfaces ➤ Index",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHint(
                paint_function=inv_paint_if_oper_status,
                title="Operational Status",
                short=None,
                _long_title_function=lambda: "Network interfaces ➤ Operational Status",
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter_class=None,
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(raw_path: str, expected: ColumnDisplayHint) -> None:
    inventory_path = cmk.gui.inventory.InventoryPath.parse(raw_path)
    hint = DISPLAY_HINTS.get_hints(inventory_path.path).get_column_hint(inventory_path.key or "")

    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)


@pytest.mark.parametrize(
    "pairs, retentions, expected",
    [
        ({}, {}, []),
        (
            {
                "b": "B",
                "d": "D",
                "c": "C",
                "a": "A",
            },
            {"c": RetentionInterval(1, 2, 3)},
            [
                ("a", "A", None),
                ("b", "B", None),
                ("d", "D", None),
                ("c", "C", 6),
            ],
        ),
    ],
)
def test_sort_attributes_pairs_displayhint(
    pairs: Mapping[SDKey, SDValue],
    retentions: Mapping[SDKey, RetentionInterval],
    expected: Sequence[tuple[SDKey, SDValue, RetentionInterval | None]],
) -> None:
    assert _sort_pairs(pairs, retentions, ["a", "b", "d", "c"]) == expected


@pytest.mark.parametrize(
    "pairs, expected",
    [
        ({}, []),
        (
            {
                "b": ("B", None),
                "d": (None, "D"),
                "c": ("C", "C"),
                "a": ("A1", "A2"),
            },
            [
                ("a", ("A1", "A2"), None),
                ("b", ("B", None), None),
                ("d", (None, "D"), None),
                ("c", ("C", "C"), None),
            ],
        ),
    ],
)
def test_sort_delta_attributes_pairs_displayhint(
    pairs: Mapping[SDKey, tuple[SDValue, SDValue]],
    expected: Sequence[tuple[SDKey, tuple[SDValue, SDValue], None]],
) -> None:
    assert _sort_pairs(pairs, {}, ["a", "b", "d", "c"]) == expected


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            tuple(),
            "key",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Key",
                short=None,
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
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Size",
                short=None,
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
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Key",
                short=None,
                _long_title_function=lambda: "Node ➤ Key",
                is_show_more=True,
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = DISPLAY_HINTS.get_hints(path).get_attribute_hint(key)

    assert hint.data_type == expected.data_type
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
    assert hint.is_show_more == expected.is_show_more


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Bar",
                short=None,
                _long_title_function=lambda: "Foo ➤ Bar",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="CPU Architecture",
                short=None,
                _long_title_function=lambda: "Processor ➤ CPU Architecture",
                is_show_more=True,
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                data_type="str",
                paint_function=inv_paint_generic,
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                title="Product",
                short=None,
                _long_title_function=lambda: "System ➤ Product",
                is_show_more=False,
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_path: str, expected: AttributeDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.InventoryPath.parse(raw_path)
    hint = DISPLAY_HINTS.get_hints(inventory_path.path).get_attribute_hint(inventory_path.key or "")

    assert hint.data_type == expected.data_type
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.title == expected.title
    assert hint.long_title == expected.long_title
    assert hint.long_inventory_title == expected.long_inventory_title
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


@pytest.mark.parametrize(
    "view_name, expected",
    [
        ("viewname", "invviewname"),
        ("invviewname", "invviewname"),
    ],
)
def test_view_spec_view_name(view_name: str, expected: str) -> None:
    table_view_spec = TableViewSpec.from_raw(tuple(), {"view": view_name})
    assert table_view_spec is not None
    assert table_view_spec.view_name == expected


def test_registered_sorter_cmp() -> None:
    hint = AttributeDisplayHint(
        data_type="str",
        paint_function=inv_paint_generic,
        sort_function=_decorate_sort_function(_cmp_inv_generic),
        title="Product",
        short=None,
        _long_title_function=lambda: "System ➤ Product",
        is_show_more=False,
    )

    _register_sorter(
        ident="test_sorter",
        long_inventory_title="A long title",
        load_inv=False,
        columns=["foobar"],
        hint=hint,
        value_extractor=lambda v: v.get("key"),
    )

    sorter_cls = sorter_registry.get("test_sorter")
    assert sorter_cls is not None
    assert sorter_cls().cmp({}, {}, None) == 0


def test_row_post_processor() -> None:
    class _FakeJoinCell(JoinCell):
        def painter_parameters(self) -> PainterParameters | None:
            return self._painter_params

    rows = [
        {
            "site": "mysite",
            "host_name": "my-host-name1",
            "invorainstance_sid": "sid1",
            "invorainstance_version": "version1",
            "invorainstance_bar": "bar",
            "host_inventory": ImmutableTree.deserialize(
                {
                    "Attributes": {},
                    "Nodes": {
                        "path-to": {
                            "Attributes": {},
                            "Nodes": {
                                "ora-dataguard-stats": {
                                    "Attributes": {},
                                    "Nodes": {},
                                    "Table": {
                                        "KeyColumns": ["sid"],
                                        "Rows": [
                                            {
                                                "sid": "sid1",
                                                "db_unique": "name1",
                                                "role": "role1",
                                                "switchover": "switchover1",
                                            },
                                            {
                                                "sid": "sid2",
                                                "db_unique": "name2",
                                                "role": "role2",
                                                "switchover": "switchover2",
                                            },
                                        ],
                                    },
                                },
                                "ora-versions": {
                                    "Attributes": {},
                                    "Nodes": {},
                                    "Table": {
                                        "KeyColumns": ["version"],
                                        "Rows": [
                                            {
                                                "version": "version1",
                                                "edition": "edition1",
                                            },
                                            {
                                                "version": "version2",
                                                "edition": "edition2",
                                            },
                                        ],
                                    },
                                },
                                "ora-foobar": {
                                    "Attributes": {},
                                    "Nodes": {},
                                    "Table": {
                                        "KeyColumns": ["foo"],
                                        "Rows": [
                                            {
                                                "foo": "foo1",
                                                "bar": "bar",
                                            },
                                            {
                                                "foo": "foo2",
                                                "bar": "bar",
                                            },
                                        ],
                                    },
                                },
                            },
                            "Table": {},
                        },
                    },
                    "Table": {},
                }
            ),
        },
    ]

    expected_len = len(rows)

    _join_inventory_rows(
        view_macros=[
            ("sid", "$SID$"),
            ("version", "$VERSION$"),
            ("bar", "$BAR$"),
        ],
        view_join_cells=[
            # Matches 'sid'
            _FakeJoinCell(
                ColumnSpec(
                    name="invoradataguardstats_db_unique",
                    parameters=PainterParameters(
                        path_to_table=("path-to", "ora-dataguard-stats"),
                        column_to_display="db_unique",
                        columns_to_match=[("sid", "$SID$")],
                    ),
                    join_value="invoradataguardstats_db_unique",
                    _column_type="join_inv_column",
                ),
                "",
            ),
            # Match 'version'
            _FakeJoinCell(
                ColumnSpec(
                    name="invoraversions_edition",
                    parameters=PainterParameters(
                        path_to_table=("path-to", "ora-versions"),
                        column_to_display="edition",
                        columns_to_match=[("version", "$VERSION$")],
                    ),
                    join_value="invoraversions_edition",
                    _column_type="join_inv_column",
                ),
                "",
            ),
            # Match 'bar', not unique
            _FakeJoinCell(
                ColumnSpec(
                    name="invorafoobar_foo",
                    parameters=PainterParameters(
                        path_to_table=("path-to", "ora-foobar"),
                        column_to_display="foo",
                        columns_to_match=[("bar", "$BAR$")],
                    ),
                    join_value="invorafoobar_foo",
                    _column_type="join_inv_column",
                ),
                "",
            ),
            # Unknown macro
            _FakeJoinCell(
                ColumnSpec(
                    name="invoradataguardstats_role",
                    parameters=PainterParameters(
                        path_to_table=("path-to", "ora-dataguard-stats"),
                        column_to_display="role",
                        columns_to_match=[("sid", "$BAZ$")],
                    ),
                    join_value="invoradataguardstats_role",
                    _column_type="join_inv_column",
                ),
                "",
            ),
            # Unknown node
            _FakeJoinCell(
                ColumnSpec(
                    name="invunknown_column_name",
                    parameters=PainterParameters(
                        path_to_table=("path-to", "somewhere-else"),
                        column_to_display="column_name",
                        columns_to_match=[("sid", "$SID$")],
                    ),
                    join_value="invunknown_column_name",
                    _column_type="join_inv_column",
                ),
                "",
            ),
        ],
        view_datasource_ident="invorainstance",
        rows=rows,
    )

    assert len(rows) == expected_len

    for row, expected_row in zip(
        rows,
        [
            {
                "site": "mysite",
                "host_name": "my-host-name1",
                "invorainstance_sid": "sid1",
                "invorainstance_version": "version1",
                "invorainstance_bar": "bar",
                "host_inventory": ImmutableTree.deserialize(
                    {
                        "Attributes": {},
                        "Nodes": {
                            "path-to": {
                                "Attributes": {},
                                "Nodes": {
                                    "ora-dataguard-stats": {
                                        "Attributes": {},
                                        "Nodes": {},
                                        "Table": {
                                            "KeyColumns": ["sid"],
                                            "Rows": [
                                                {
                                                    "sid": "sid1",
                                                    "db_unique": "name1",
                                                    "role": "role1",
                                                    "switchover": "switchover1",
                                                },
                                                {
                                                    "sid": "sid2",
                                                    "db_unique": "name2",
                                                    "role": "role2",
                                                    "switchover": "switchover2",
                                                },
                                            ],
                                        },
                                    },
                                    "ora-versions": {
                                        "Attributes": {},
                                        "Nodes": {},
                                        "Table": {
                                            "KeyColumns": ["version"],
                                            "Rows": [
                                                {
                                                    "version": "version1",
                                                    "edition": "edition1",
                                                },
                                                {
                                                    "version": "version2",
                                                    "edition": "edition2",
                                                },
                                            ],
                                        },
                                    },
                                    "ora-foobar": {
                                        "Attributes": {},
                                        "Nodes": {},
                                        "Table": {
                                            "KeyColumns": ["foo"],
                                            "Rows": [
                                                {
                                                    "foo": "foo1",
                                                    "bar": "bar",
                                                },
                                                {
                                                    "foo": "foo2",
                                                    "bar": "bar",
                                                },
                                            ],
                                        },
                                    },
                                },
                                "Table": {},
                            },
                        },
                        "Table": {},
                    }
                ),
                "JOIN": {
                    "invoradataguardstats_db_unique": {"invoradataguardstats_db_unique": "name1"},
                    "invoraversions_edition": {"invoraversions_edition": "edition1"},
                },
            },
        ],
    ):
        assert set(row) == set(expected_row)

        assert row["site"] == expected_row["site"]
        assert row["host_name"] == expected_row["host_name"]
        assert row["invorainstance_sid"] == expected_row["invorainstance_sid"]
        assert row["invorainstance_version"] == expected_row["invorainstance_version"]
        assert row["JOIN"] == expected_row["JOIN"]
        assert row["host_inventory"] == expected_row["host_inventory"]
