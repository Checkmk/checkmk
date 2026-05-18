#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusResponse, LivestatusRow, OnlySites

import cmk.gui.inventory
import cmk.gui.utils
from cmk.ccc.user import UserId
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views.inventory._data_sources import RowTableInventory, RowTableInventoryHistory

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
    """A minimal synthetic view for the RowTableInventory.query tests.

    The tests below only consume `view.datasource` (a `hosts` datasource is
    sufficient — the row table classes mock out `_get_raw_data`) and don't
    inspect any view-spec field, so we construct the smallest valid
    `ViewSpec` here instead of fishing a plug-in-provided view out of
    `multisite_builtin_views`.
    """
    view_spec = ViewSpec(
        name="synthetic_test_view",
        datasource="hosts",
        title="synthetic test view",
        description="",
        owner=UserId.builtin(),
        public=True,
        hidden=False,
        hidebutton=True,
        topic="other",
        sort_index=99,
        is_show_more=False,
        icon=None,
        single_infos=[],
        context={},
        link_from={},
        add_context_to_title=False,
        packaged=False,
        main_menu_search_terms=[],
        layout="table",
        num_columns=1,
        browser_reload=0,
        column_headers="pergroup",
        user_sortable=True,
        play_sounds=False,
        force_checkboxes=False,
        mustsearch=False,
        mobile=False,
        group_painters=[],
        painters=[],
        sorters=[],
    )
    return View(
        "synthetic_test_view",
        view_spec,
        view_spec.get("context", {}),
        UserPermissions({}, {}, {}, []),
    )


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
        "invtesttable", cmk.gui.inventory.parse_internal_raw_path(".foo.bar:")
    )
    rows, _len_rows = row_table.query(view.datasource, [], [], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_unknown_columns(view: View) -> None:
    row_table = RowTableInventoryTest1(
        "invtesttable", cmk.gui.inventory.parse_internal_raw_path(".foo.bar:")
    )
    rows, _len_rows = row_table.query(view.datasource, [], ["foo"], {}, "", None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


@pytest.mark.usefixtures("request_context")
def test_query_row_table_inventory_add_columns(view: View) -> None:
    row_table = RowTableInventoryTest2(
        "invtesttable", cmk.gui.inventory.parse_internal_raw_path(".foo.bar:")
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
