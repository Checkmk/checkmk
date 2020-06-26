# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def test_openapi_hosts(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"hostname": "foobar", "folder": "root"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.follow_link(
        resp,
        'self',
        base=base,
        status=200,
    )

    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        base=base,
        status=200,
        params='{"attributes": {}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    wsgi_app.follow_link(
        resp,
        '.../delete',
        base=base,
        status=204,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
