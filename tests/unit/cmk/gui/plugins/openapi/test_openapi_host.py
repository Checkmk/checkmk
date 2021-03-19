#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_livestatus_hosts_generic_filter(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('hosts', [
        {
            'name': 'heute',
            'address': '127.0.0.1',
            'alias': 'heute',
            'downtimes_with_info': [],
            'scheduled_downtime_depth': 0,
        },
    ])

    live.expect_query([
        'GET hosts',
        'Columns: name',
    ],)
    with live:
        resp = wsgi_app.call_method(
            'get',
            base + "/domain-types/host/collections/all",
            status=200,
        )
        assert len(resp.json['value']) == 1

    live.expect_query([
        'GET hosts',
        'Columns: name',
        'Filter: alias ~ heute',
    ],)
    with live:
        resp = wsgi_app.call_method(
            'get',
            base +
            '/domain-types/host/collections/all?query={"op": "~", "left": "alias", "right": "heute"}',
            status=200,
        )
        assert len(resp.json['value']) == 1
