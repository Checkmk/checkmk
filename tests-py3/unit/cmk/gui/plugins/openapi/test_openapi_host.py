# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_livestatus_hosts(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    host_result = [['heute', '127.0.0.1', 'heute', [], 0]]

    live.expect_query(
        [
            'GET hosts',
            'Columns: name address alias downtimes_with_info scheduled_downtime_depth',
        ],
        result=host_result,
    )
    with live:
        resp = wsgi_app.call_method(
            'get',
            base + "/domain-types/host/collections/all",
            status=200,
        )
        assert len(resp.json['value']) == 1

    live.expect_query(
        [
            'GET hosts',
            'Columns: name address alias downtimes_with_info scheduled_downtime_depth',
            'Filter: alias ~ heute',
        ],
        result=host_result,
    )
    with live:
        resp = wsgi_app.call_method(
            'get',
            base + "/domain-types/host/collections/all?host_alias=heute",
            status=200,
        )
        assert len(resp.json['value']) == 1
