#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_livestatus_acknowledgements(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.expect_query(
        [
            'GET services',
            'Columns: description state',
            'Filter: description = Memory',
            'Filter: host_name = heute',
            'And: 2',
        ],
        result=[['Memory', 1]],
    ).expect_query(
        'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;Memory;2;1;1;test123-...;Hello world!',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + "/objects/host/heute/objects/service/Memory/actions/acknowledge",
            params=json.dumps({
                'sticky': True,
                'notify': True,
                'persistent': True,
                'comment': 'Hello world!',
            }),
            content_type='application/json',
            status=204,
        )
