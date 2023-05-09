#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_wato_disabled_blocks_query(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    # add a host, so we can query it
    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "neute", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    live.expect_query([
        'GET services',
        'Columns: host_name description',
    ])

    # calls to setup endpoints work correctly
    wsgi_app.call_method(
        'get',
        base + "/objects/host_config/neute",
        status=200,
    )

    # disable wato
    with wsgi_app.set_config(wato_enabled=False):
        # calls to setup endpoints are forbidden
        wsgi_app.call_method(
            'get',
            base + "/objects/host_config/neute",
            status=403,
        )
        with live:
            # calls to monitoring endpoints should be allowed
            wsgi_app.call_method(
                'get',
                base + "/domain-types/service/collections/all",
                status=200,
            )
