#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.plugins.views import RowTableLivestatus
from cmk.gui.views import View


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
