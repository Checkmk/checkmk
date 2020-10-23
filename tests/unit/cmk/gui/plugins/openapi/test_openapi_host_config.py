#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json


def test_openapi_cluster_host(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "root"}',
        status=200,
        content_type='application/json',
    )

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/clusters",
        params='{"host_name": "bazfoo", "folder": "root", "nodes": ["foobar"]}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/bazfoo",
        status=200,
    )

    wsgi_app.call_method(
        'put',
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": []}',
        status=200,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/bazfoo",
        status=200,
    )
    assert resp.json['extensions']['cluster_nodes'] == []


def test_openapi_hosts(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "root"}',
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
        params='{"attributes": {"ipaddress": "127.0.0.1"}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    # also try to update with wrong attribute

    wsgi_app.follow_link(
        resp,
        '.../update',
        base=base,
        status=400,
        params='{"attributes": {"foobaz": "bar"}}',
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


def test_openapi_bulk_hosts(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps({
            "entries": [
                {
                    "host_name": "foobar",
                    "folder": "root",
                    "attributes": {
                        "ipaddress": "127.0.0.2"
                    }
                },
                {
                    "host_name": "sample",
                    "folder": "root",
                    "attributes": {
                        "ipaddress": "127.0.0.2"
                    }
                },
            ]
        }),
        status=200,
        content_type='application/json',
    )
    assert len(resp.json['value']) == 2

    _resp = wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            "entries": [{
                "host_name": "foobar",
                "attributes": {
                    "ipaddress": "192.168.1.1"
                },
            }],
        }),
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )
    assert resp.json['extensions']['attributes']['ipaddress'] == "192.168.1.1"

    _resp = wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            "entries": [{
                "host_name": "foobar",
                "attributes": {
                    "foobaz": "bar"
                }
            }],
        }),
        status=400,
        content_type='application/json',
    )
