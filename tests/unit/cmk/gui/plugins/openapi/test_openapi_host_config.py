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
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/clusters",
        params='{"host_name": "bazfoo", "folder": "/", "nodes": ["foobar"]}',
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
        params='{"host_name": "foobar", "folder": "/"}',
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
    assert resp.json['extensions']['attributes'] == {'ipaddress': '127.0.0.1'}

    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        base=base,
        status=200,
        params='{"update_attributes": {"alias": "bar"}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
    assert resp.json['extensions']['attributes'] == {'ipaddress': '127.0.0.1', 'alias': 'bar'}

    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        base=base,
        status=200,
        params='{"remove_attributes": ["alias"]}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
    assert resp.json['extensions']['attributes'] == {'ipaddress': '127.0.0.1'}
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
                    "folder": "/",
                    "attributes": {
                        "ipaddress": "127.0.0.2"
                    }
                },
                {
                    "host_name": "sample",
                    "folder": "/",
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


def test_openapi_host_rename(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=200,
    )

    _resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobaz",
        status=200,
    )


def test_openapi_host_rename_error_on_not_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/fooba/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=404,
    )


def test_openapi_host_rename_on_invalid_hostname(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobar"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=400,
    )


def test_openapi_host_rename_with_pending_activate_changes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=409,
    )


def test_openapi_host_move(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type='application/json',
        status=200,
    )

    _resp = wsgi_app.call_method(
        'post',
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
        status=200,
    )


def test_openapi_host_move_to_non_valid_folder(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type='application/json',
        status=200,
    )

    _resp = wsgi_app.call_method(
        'post',
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/"}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
        status=400,
    )


def test_openapi_host_move_of_non_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    _resp = wsgi_app.call_method(
        'post',
        base + "/objects/host_config/foobaz/actions/move/invoke",
        params='{"target_folder": "/"}',
        content_type='application/json',
        status=404,
    )
