#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui import sites
from cmk.gui.plugins.views import RowTableLivestatus
from cmk.gui.plugins.wato.ac_tests import ACTestGenericCheckHelperUsage
from cmk.gui.views import View
from livestatus import intercept_queries


def test_local_connection_mocked(mock_livestatus):
    live = mock_livestatus
    live.expect_query('GET status\nColumns: helper_usage_generic average_latency_generic\n')
    with live(expect_status_query=False):
        gen = ACTestGenericCheckHelperUsage().execute()
        list(gen)


def test_row_table_object(mock_livestatus, register_builtin_html):
    live = mock_livestatus
    live.add_table(
        'hosts',
        [{
            'name': 'heute',
            'alias': 'heute',
            'host_state': 0,
            'host_has_been_checked': False,
        }],
    )
    live.expect_query('GET hosts\n'
                      'Columns: name host_has_been_checked host_state\n'
                      'Filter: name = heute')

    view_name = "hosts"
    view_spec = {
        "datasource": "hosts",
        "painters": [],
    }
    context = {
        'host': 'heute',
        'service': None,
    }
    view = View(view_name, view_spec, context)
    rt = RowTableLivestatus("hosts")

    with live(expect_status_query=True):
        rt.query(
            view=view,
            columns=['name'],
            headers='Filter: name = heute',
            only_sites=None,
            limit=None,
            all_active_filters=[],
        )


def test_intercept_queries(mock_livestatus, register_builtin_html):
    with mock_livestatus(expect_status_query=True):
        live = sites.live()

    mock_livestatus.expect_query("GET hosts\nColumns: name")
    with mock_livestatus(expect_status_query=False), intercept_queries() as queries:
        live.query("GET hosts\nColumns: name")

    # livestatus.py appends a lot of extra columns, so we only check for startswith
    assert queries[0].startswith("GET hosts\nColumns: name\n")
