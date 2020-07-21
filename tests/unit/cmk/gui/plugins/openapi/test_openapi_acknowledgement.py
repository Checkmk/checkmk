#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest  # type: ignore[import]

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.gui.plugins.openapi.restful_objects.constructors import url_safe


@pytest.mark.parametrize(
    argnames=[
        'service',
        'http_response_code',
    ],
    argvalues=[
        ['Memory', 204],  # ack ok
        ['Filesystem /boot', 204],  # slashes in name, ack ok
        ['CPU load', 400],  # service OK, nothing to ack, 400
    ])
def test_openapi_livestatus_acknowledgements(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    service,
    http_response_code,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('services', [
        {
            'host_name': 'heute',
            'description': 'Memory',
            'state': 1
        },
        {
            'host_name': 'heute',
            'description': 'CPU load',
            'state': 0
        },
        {
            'host_name': 'heute',
            'description': 'Filesystem /boot',
            'state': 1
        },
    ])

    live.expect_query([
        'GET services',
        'Columns: description state',
        f'Filter: description = {service}',
        'Filter: host_name = heute',
        'And: 2',
    ])

    if http_response_code == 204:
        live.expect_query(
            f'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;{service};2;1;1;test123-...;Hello world!',
            match_type='ellipsis',
        )

    with live:
        wsgi_app.post(
            base + f"/objects/host/heute/objects/service/{url_safe(service)}/actions/acknowledge",
            params=json.dumps({
                'sticky': True,
                'notify': True,
                'persistent': True,
                'comment': 'Hello world!',
            }),
            content_type='application/json',
            status=http_response_code,
        )
