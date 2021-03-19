#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import string

import pytest  # type: ignore[import]


@pytest.mark.parametrize("group_type", ['host', 'contact', 'service'])
def test_openapi_groups(group_type, wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    name = _random_string(10)
    alias = _random_string(10)

    group = {'name': name, 'alias': alias}

    base = "/NO_SITE/check_mk/api/v0"
    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/%s_group_config/collections/all" % (group_type,),
        params=json.dumps(group),
        status=200,
        content_type='application/json',
    )

    _ = wsgi_app.call_method(
        'get',
        base + "/domain-types/%s_group_config/collections/all" % (group_type,),
        status=200,
    )

    resp = wsgi_app.follow_link(
        resp,
        'self',
        base=base,
        status=200,
    )

    group['name'] += " updated"
    # group['alias'] += " alolo"

    wsgi_app.follow_link(
        resp,
        '.../update',
        base=base,
        params=json.dumps(group),
        headers={'If-Match': 'foo bar'},
        status=412,
        content_type='application/json',
    )

    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        base=base,
        params=json.dumps(group),
        headers={'If-Match': resp.headers['ETag']},
        status=200,
        content_type='application/json',
    )

    wsgi_app.follow_link(
        resp,
        '.../delete',
        base=base,
        headers={'If-Match': resp.headers['ETag']},
        status=204,
        content_type='application/json',
    )


@pytest.mark.parametrize("group_type", ['host', 'service', 'contact'])
def test_openapi_bulk_groups(group_type, wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    groups = [{'name': _random_string(10), 'alias': _random_string(10)} for _i in range(2)]

    base = "/NO_SITE/check_mk/api/v0"
    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/%s_group_config/actions/bulk-create/invoke" % (group_type,),
        params=json.dumps({'entries': groups}),
        status=200,
        content_type='application/json',
    )
    assert len(resp.json['value']) == 2

    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/%s_group_config/actions/bulk-create/invoke" % (group_type,),
        params=json.dumps({'entries': groups}),
        status=400,
        content_type='application/json',
    )

    update_groups = [{
        'name': group['name'],
        'attributes': {
            'name': f"{group['name']} updated",
            'alias': group['alias'],
        },
    } for group in groups]

    _resp = wsgi_app.call_method(
        'put',
        base + "/domain-types/%s_group_config/actions/bulk-update/invoke" % (group_type,),
        params=json.dumps({'entries': update_groups}),
        status=200,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'delete',
        base + "/domain-types/%s_group_config/actions/bulk-delete/invoke" % (group_type,),
        params=json.dumps({'entries': [f"{group['name']}" for group in groups]}),
        status=204,
        content_type='application/json',
    )


def _random_string(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))
