#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection

CMK_WAIT_FOR_COMPLETION = 'cmk/wait-for-completion'


def test_openapi_activate_changes(
    wsgi_app,
    suppress_automation_calls,
    with_automation_user,
    mock_livestatus: MockLiveStatusConnection,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/v0"

    # We create a host
    live = mock_livestatus

    host_created = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    with live(expect_status_query=True):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=400,
            params='{"sites": ["asdf"]}',
            content_type='application/json',
        )
        assert resp.json['detail'].startswith("Unknown site")

        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=200,
        )

    with live(expect_status_query=True):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=301,
            params='{"redirect": true}',
            content_type='application/json',
        )

    for _ in range(10):
        resp = wsgi_app.follow_link(
            resp,
            CMK_WAIT_FOR_COMPLETION,
            base=base,
        )
        if resp.status_code == 204:
            break

    # We delete the host again

    wsgi_app.follow_link(
        host_created,
        '.../delete',
        base=base,
        status=204,
        headers={'If-Match': host_created.headers['ETag']},
        content_type='application/json',
    )

    # And activate the changes

    with live(expect_status_query=True):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
        )

    for _ in range(10):
        resp = wsgi_app.follow_link(
            resp,
            CMK_WAIT_FOR_COMPLETION,
            base=base,
        )
        if resp.status_code == 204:
            break
