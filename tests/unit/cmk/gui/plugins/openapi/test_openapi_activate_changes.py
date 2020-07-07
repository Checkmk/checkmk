#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def test_openapi_activate_changes(wsgi_app, suppress_automation_calls, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/v0"

    # We create a host

    host_created = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "root"}',
        status=200,
        content_type='application/json',
    )

    # And activate the changes

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/activation_run/actions/activate-changes/invoke",
    )

    for _ in range(10):
        resp = wsgi_app.follow_link(
            resp,
            'cmk/wait-for-completion',
            base=base,
        )
        if resp.status == 204:
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

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/activation_run/actions/activate-changes/invoke",
    )

    for _ in range(10):
        resp = wsgi_app.follow_link(
            resp,
            'cmk/wait-for-completion',
            base=base,
        )
        if resp.status == 204:
            break
