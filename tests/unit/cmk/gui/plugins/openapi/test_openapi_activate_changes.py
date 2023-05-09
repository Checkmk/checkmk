#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.gui.plugins.openapi.restful_objects import constructors

CMK_WAIT_FOR_COMPLETION = 'cmk/wait-for-completion'


def test_openapi_show_activations(
    wsgi_app,
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        'get',
        base + '/objects/activation_run/asdf/actions/wait-for-completion/invoke',
        status=404,
    )


def test_openapi_list_currently_running_activations(
    wsgi_app,
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        'get',
        base + constructors.collection_href('activation_run', 'running'),
        status=200,
    )


def test_openapi_activate_changes(
    wsgi_app,
    suppress_automation_calls,
    with_automation_user,
    mock_livestatus: MockLiveStatusConnection,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

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
        assert "Unknown site" in repr(resp.json), resp.json

        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=200,
            content_type='application/json',
        )

    with live(expect_status_query=True):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=302,
            params='{"redirect": true}',
            content_type='application/json',
        )

    for _ in range(10):
        resp = wsgi_app.follow_link(
            resp,
            CMK_WAIT_FOR_COMPLETION,
        )
        if resp.status_code == 204:
            break

    # We delete the host again

    wsgi_app.follow_link(
        host_created,
        '.../delete',
        status=204,
        headers={'If-Match': host_created.headers['ETag']},
        content_type='application/json',
    )

    # And activate the changes

    with live(expect_status_query=True):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            content_type="application/json",
        )

    for _ in range(10):
        resp = wsgi_app.follow_link(
            resp,
            CMK_WAIT_FOR_COMPLETION,
        )
        if resp.status_code == 204:
            break


def test_openapi_activate_changes_nothing_to_perform(
    wsgi_app,
    suppress_automation_calls,
    with_automation_user,
    mock_livestatus: MockLiveStatusConnection,
    inline_background_jobs,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    # We create a host
    live = mock_livestatus

    _host_created = wsgi_app.call_method(
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
        assert "Unknown site" in repr(resp.json), resp.json

        _resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=200,
            content_type='application/json',
        )

        _resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=422,
            content_type='application/json',
        )
