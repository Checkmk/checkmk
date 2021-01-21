# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json


def test_openapi_host_tag_group(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps({
            "ident": "foo",
            "title": "foobar",
            "topic": "nothing",
            "tags": [{
                "ident": "tester",
                "title": "something",
            }]
        }),
        status=200,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_tag_group/foo",
        params=json.dumps({"tags": [{
            "ident": "tutu",
            "title": "something",
        }]}),
        headers={'If-Match': resp.headers['ETag']},
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_tag_group/foo",
        status=200,
    )
    assert resp.json["extensions"] == {
        'tags': [{
            'id': 'tutu',
            'title': 'something',
            'aux_tags': []
        }],
        'topic': 'nothing'
    }

    _resp = wsgi_app.call_method(
        'delete',
        base + "/objects/host_tag_group/foo",
        params=json.dumps({}),
        headers={'If-Match': resp.headers['ETag']},
        status=204,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_tag_group/foo",
        status=400,
    )


def test_openapi_host_tag_group_invalid_id(wsgi_app, with_automation_user,
                                           suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'
    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps({
            "ident": "1",
            "title": "Kubernetes",
            "topic": "Data Sources",
            "help": "Kubernetes Pods",
            "tags": [{
                "ident": "pod",
                "title": "Pod"
            }]
        }),
        status=400,
        content_type='application/json',
    )
