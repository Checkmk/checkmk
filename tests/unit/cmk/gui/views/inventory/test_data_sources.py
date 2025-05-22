#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusResponse, LivestatusRow, OnlySites

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.view import View
from cmk.gui.views.inventory._data_sources import RowTableInventory, RowTableInventoryHistory
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
