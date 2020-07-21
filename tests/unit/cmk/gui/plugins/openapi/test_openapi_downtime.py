#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_livestatus_downtimes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('downtimes', [{
        'id': 54,
        'host_name': 'heute',
        'service_description': 'CPU load',
        'is_service': 1,
        'author': 'cmkadmin',
        'start_time': 1593770319,
        'end_time': 1596448719,
        'recurring': 0,
        'comment': 'Downtime for service',
    }])

    live.expect_query([
        'GET downtimes',
        'Columns: id host_name service_description is_service author start_time end_time recurring comment'
    ])
    with live:
        resp = wsgi_app.call_method('get',
                                    base + "/domain-types/downtime/collections/all",
                                    status=200)
        assert len(resp.json['value']) == 1
