# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.utils.tags import BuiltinTagConfig


def test_openapi_host_tag_group_update(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

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


def test_openapi_host_tag_group_get_collection(wsgi_app, with_automation_user,
                                               suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    builtin_groups_count = len(BuiltinTagConfig().tag_groups)

    col_resp = wsgi_app.call_method(
        'get',
        base + '/domain-types/host_tag_group/collections/all',
        status=200,
    )
    assert len(col_resp.json_body["value"]) == builtin_groups_count


def test_openapi_host_tag_group_delete(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

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
        status=404,
    )


def test_openapi_host_tag_group_invalid_id(wsgi_app, with_automation_user,
                                           suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'
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


def test_openapi_host_tag_group_built_in(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'get',
        base + '/domain-types/host_tag_group/collections/all',
        status=200,
    )
    built_in_tags = [tag_group.title for tag_group in BuiltinTagConfig().tag_groups]
    assert all(
        [title in (entry['title'] for entry in resp.json_body['value']) for title in built_in_tags])

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_tag_group/agent",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_tag_group/agent",
        params=json.dumps({"tags": [{
            "ident": "tutu",
            "title": "something",
        }]}),
        headers={'If-Match': resp.headers['ETag']},
        status=405,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'delete',
        base + "/objects/host_tag_group/agent",
        params=json.dumps({}),
        status=405,
        content_type='application/json',
    )
