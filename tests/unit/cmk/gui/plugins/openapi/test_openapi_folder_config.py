#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import uuid


def test_openapi_folder_validation(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
        params=
        '{"name": "new_folder", "title": "foo", "parent": "abababaabababaababababbbabababab"}',
        status=400,
        content_type='application/json',
    )

    wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/", "attributes": {"foo": "bar"}}',
        status=400,
        content_type='application/json',
    )


def test_openapi_folders(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    resp = wsgi_app.call_method(
        'get',
        "/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
        status=200,
    )
    assert resp.json['value'] == []

    other_folder = wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
        params='{"name": "other_folder", "title": "bar", "parent": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = new_folder = wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        content_type='application/json',
    )

    wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
        params='{"name": "sub_folder", "title": "foo", "parent": "/new_folder"}',
        status=200,
        content_type='application/json',
    )

    base = '/NO_SITE/check_mk/api/v0'

    # First test without the proper ETag, fails with 412 (precondition failed)
    wsgi_app.follow_link(resp,
                         '.../update',
                         base=base,
                         status=412,
                         params='{"title": "foobar"}',
                         content_type='application/json')
    wsgi_app.follow_link(resp,
                         '.../update',
                         base=base,
                         status=412,
                         headers={'If-Match': 'Witty Sensationalist Header!'},
                         params='{"title": "foobar"}',
                         content_type='application/json')
    # With the right ETag, the operation shall succeed
    resp = wsgi_app.follow_link(resp,
                                '.../update',
                                base=base,
                                status=200,
                                headers={'If-Match': resp.headers['ETag']},
                                params='{"title": "foobar"}',
                                content_type='application/json')
    # Even twice, as this is idempotent.
    resp = wsgi_app.follow_link(resp,
                                '.../update',
                                base=base,
                                status=200,
                                headers={'If-Match': resp.headers['ETag']},
                                params='{"title": "foobar"}',
                                content_type='application/json')

    # Move to the same source should give a 400
    wsgi_app.follow_link(resp,
                         '.../invoke;action="move"',
                         base=base,
                         status=400,
                         headers={'If-Match': resp.headers['ETag']},
                         params=json.dumps({"destination": '/'}),
                         content_type='application/json')

    # Check that unknown folders also give a 400
    wsgi_app.follow_link(resp,
                         '.../invoke;action="move"',
                         base=base,
                         status=400,
                         headers={'If-Match': resp.headers['ETag']},
                         params=json.dumps({"destination": 'asdf'}),
                         content_type='application/json')

    # Check that moving onto itself gives a 400
    wsgi_app.follow_link(other_folder,
                         '.../invoke;action="move"',
                         base=base,
                         status=400,
                         headers={'If-Match': other_folder.headers['ETag']},
                         params=json.dumps({"destination": '/other_folder'}),
                         content_type='application/json')

    # Check that moving into it's own subfolder is not possible.
    wsgi_app.follow_link(new_folder,
                         '.../invoke;action="move"',
                         base=base,
                         status=400,
                         headers={'If-Match': resp.headers['ETag']},
                         params=json.dumps({"destination": '/new_folder/sub_folder'}),
                         content_type='application/json')

    wsgi_app.follow_link(new_folder,
                         '.../invoke;action="move"',
                         base=base,
                         status=200,
                         headers={'If-Match': resp.headers['ETag']},
                         params=json.dumps({"destination": '/other_folder'}),
                         content_type='application/json')

    # Delete all folders.
    coll = wsgi_app.get("/NO_SITE/check_mk/api/v0/domain-types/folder_config/collections/all",
                        status=200)
    for entry in coll.json['value']:
        # Fetch the new E-Tag.
        resp = wsgi_app.get("/NO_SITE/check_mk/api/v0" + entry['href'], status=200)
        # With the right ETag, the operation shall succeed
        wsgi_app.follow_link(resp,
                             '.../delete',
                             base=base,
                             status=204,
                             headers={'If-Match': resp.headers['ETag']})


def test_openapi_missing_folder(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    resp = wsgi_app.get("/NO_SITE/check_mk/api/v0/objects/folder_config/asdf" + uuid.uuid4().hex,
                        status=400)
    assert 'title' in resp.json
