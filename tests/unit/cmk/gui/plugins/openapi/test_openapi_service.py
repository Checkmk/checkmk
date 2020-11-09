#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_livestatus_service(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Filesystem /opt/omd/sites/heute/tmp',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example.com',
                'host_alias': 'example.com',
                'description': 'Filesystem /boot',
                'state': 0,
                'state_type': 'hard',
                'last_check': 0,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query([
        'GET services',
        'Columns: host_name description',
    ],)

    with live:
        base = '/NO_SITE/check_mk/api/v0'

        resp = wsgi_app.call_method(
            'get',
            base + "/domain-types/service/collections/all",
            status=200,
        )
        assert len(resp.json['value']) == 2

    live.expect_query([
        'GET services',
        'Columns: host_name description',
        'Filter: host_alias ~ heute',
    ],)

    with live:
        resp = wsgi_app.call_method(
            'get',
            base +
            '/domain-types/service/collections/all?query={"op": "~", "left": "services.host_alias", "right": "heute"}',
            status=200,
        )
        assert len(resp.json['value']) == 1

    live.expect_query([
        'GET services',
        'Columns: host_name description',
        'Filter: host_name = example.com',
    ])
    with live:
        resp = wsgi_app.call_method(
            'get',
            base + "/objects/host/example.com/collections/services",
            status=200,
        )
        assert len(resp.json['value']) == 1
