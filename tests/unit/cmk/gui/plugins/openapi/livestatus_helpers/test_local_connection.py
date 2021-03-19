#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import livestatus
from cmk.gui import sites
from cmk.gui.plugins.views import RowTableLivestatus
from cmk.gui.plugins.wato.ac_tests import ACTestGenericCheckHelperUsage
from cmk.gui.views import View


def test_local_connection_mocked(mock_livestatus):
    live = mock_livestatus
    live.set_sites(['local'])
    live.expect_query([
        'GET status',
        'Columns: helper_usage_generic average_latency_generic',
        'ColumnHeaders: off',
    ])
    with live(expect_status_query=False):
        gen = ACTestGenericCheckHelperUsage().execute()
        list(gen)


def test_local_table_assoc(mock_livestatus):
    live = mock_livestatus
    live.set_sites(["local"])
    live.add_table(
        "hosts",
        [{
            'name': 'example.com',
            'alias': 'example.com alias',
            'address': 'server.example.com',
            'custom_variables': {
                "FILENAME": "/wato/hosts.mk",
                "ADDRESS_FAMILY": "4",
                "ADDRESS_4": "127.0.0.1",
                "ADDRESS_6": "",
                "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
            },
            'contacts': [],
            'contact_groups': ['all'],
        }],
        site="local",
    )
    live.expect_query([
        "GET hosts", "Columns: name alias address custom_variables contacts contact_groups",
        "ColumnHeaders: on"
    ])
    with live(expect_status_query=False):
        livestatus.LocalConnection().query_table_assoc(
            "GET hosts\n"
            "Columns: name alias address custom_variables contacts contact_groups")


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
                      'Columns: host_has_been_checked host_state name\n'
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
    with mock_livestatus(expect_status_query=False), livestatus.intercept_queries() as queries:
        live.query("GET hosts\nColumns: name")

    # livestatus.py appends a lot of extra columns, so we only check for startswith
    assert queries[0].startswith("GET hosts\nColumns: name\n")
