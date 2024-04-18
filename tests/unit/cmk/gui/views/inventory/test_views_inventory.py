#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusResponse, LivestatusRow, OnlySites

from cmk.utils.structured_data import ImmutableTree, SDNodeName

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.painter.v0.base import JoinCell
from cmk.gui.type_defs import ColumnSpec, PainterParameters
from cmk.gui.view import View
from cmk.gui.views.inventory import RowTableInventory, RowTableInventoryHistory
from cmk.gui.views.inventory.row_post_processor import _join_inventory_rows
from cmk.gui.views.store import multisite_builtin_views

EXPECTED_INV_KEYS = [
    "site",
    "host_name",
    "invtesttable_sid",
    "invtesttable_sid_retention_interval",
    "invtesttable_value1",
    "invtesttable_value1_retention_interval",
    "invtesttable_value2",
    "invtesttable_value2_retention_interval",
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


@pytest.fixture(name="view")
def fixture_view() -> View:
    """Provide some arbitrary view for testing"""
    view_spec = multisite_builtin_views["invinterface_of_host"]
    return View("invdockerimages", view_spec, view_spec["context"])


class RowTableInventoryTest1(RowTableInventory):
    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        return LivestatusResponse([LivestatusRow(["this_site", "this_hostname"])])


class RowTableInventoryTest2(RowTableInventory):
    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        return LivestatusResponse([LivestatusRow(["this_site", "this_hostname", "foobar"])])


class RowTableInventoryHistoryTest1(RowTableInventoryHistory):
    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        return LivestatusResponse([LivestatusRow(["this_site", "this_hostname"])])


class RowTableInventoryHistoryTest2(RowTableInventoryHistory):
    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        return LivestatusResponse([LivestatusRow(["this_site", "this_hostname", "foobar"])])


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory(view: View) -> None:
    row_table = RowTableInventoryTest1(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    rows, _len_rows = row_table.query(view.datasource, [], [], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_unknown_columns(view: View) -> None:
    row_table = RowTableInventoryTest1(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    rows, _len_rows = row_table.query(view.datasource, [], ["foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_add_columns(view: View) -> None:
    row_table = RowTableInventoryTest2(
        "invtesttable", cmk.gui.inventory.InventoryPath.parse(".foo.bar:")
    )
    rows, _len_rows = row_table.query(view.datasource, [], ["host_foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS + ["host_foo"])


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history(view: View) -> None:
    row_table = RowTableInventoryHistoryTest1()
    rows, _len_rows = row_table.query(view.datasource, [], [], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history_unknown_columns(view: View) -> None:
    row_table = RowTableInventoryHistoryTest1()
    rows, _len_rows = row_table.query(view.datasource, [], ["foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_history_add_columns(view: View) -> None:
    row_table = RowTableInventoryHistoryTest2()
    rows, _len_rows = row_table.query(view.datasource, [], ["host_foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS + ["host_foo"])


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
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-dataguard-stats")),
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
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-versions")),
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
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-foobar")),
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
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-dataguard-stats")),
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
                        path_to_table=(SDNodeName("path-to"), SDNodeName("somewhere-else")),
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
