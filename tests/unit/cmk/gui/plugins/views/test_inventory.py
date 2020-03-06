#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.plugins.views.inventory as inventory

RAW_ROWS = [('this_site', 'this_hostname')]
RAW_ROWS2 = [('this_site', 'this_hostname', 'foobar')]

INV_ROWS = [
    {
        'sid': 'A',
        'value1': 1,
        'value2': 4
    },
    {
        'sid': 'B',
        'value1': 2,
        'value2': 5
    },
    {
        'sid': 'C',
        'value1': 3,
        'value2': 6
    },
]

EXPECTED_INV_KEYS = [
    'site',
    'host_name',
    'invtesttable_sid',
    'invtesttable_value1',
    'invtesttable_value2',
]

INV_HIST_ROWS = [
    (123, (1, 2, 3, None)),
    (456, (4, 5, 6, None)),
    (789, (7, 8, 9, None)),
]

EXPECTED_INV_HIST_KEYS = [
    'site',
    'host_name',
    "invhist_time",
    "invhist_delta",
    "invhist_removed",
    "invhist_new",
    "invhist_changed",
]


def test_query_row_table_inventory(monkeypatch):
    row_table = inventory.RowTableInventory("invtesttable", ".foo.bar:")
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows = row_table.query(None, [], None, None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


def test_query_row_table_inventory_unknown_columns(monkeypatch):
    row_table = inventory.RowTableInventory("invtesttable", ".foo.bar:")
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows = row_table.query(None, ['foo'], None, None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS)


def test_query_row_table_inventory_add_columns(monkeypatch):
    row_table = inventory.RowTableInventory("invtesttable", ".foo.bar:")
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_ROWS)
    rows = row_table.query(None, ['host_foo'], None, None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_KEYS + ['host_foo'])


def test_query_row_table_inventory_history(monkeypatch):
    row_table = inventory.RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows = row_table.query(None, [], None, None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


def test_query_row_table_inventory_history_unknown_columns(monkeypatch):
    row_table = inventory.RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows = row_table.query(None, ['foo'], None, None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS)


def test_query_row_table_inventory_history_add_columns(monkeypatch):
    row_table = inventory.RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_raw_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_inv_data", lambda hostrow: INV_HIST_ROWS)
    rows = row_table.query(None, ['host_foo'], None, None, None, [])
    for row in rows:
        assert set(row) == set(EXPECTED_INV_HIST_KEYS + ['host_foo'])
