#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import random
import string
import typing
import uuid

import pytest

import cmk.utils.paths
import cmk.utils.version as cmk_version

if typing.TYPE_CHECKING:
    import webtest  # pylint: disable=unused-import

# pylint: disable=redefined-outer-name


def test_normal_auth(
    wsgi_app,  # type: WebTestAppForCMK
    with_user,
):
    username, password = with_user
    login = wsgi_app.get('/NO_SITE/check_mk/login.py')  # type: webtest.TestResponse
    login.form['_username'] = username
    login.form['_password'] = password
    resp = login.form.submit('_login', index=1)

    assert "Invalid credentials." not in resp.body


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No agent deployment in raw edition")
def test_deploy_agent(wsgi_app):
    response = wsgi_app.get('/NO_SITE/check_mk/deploy_agent.py')
    assert response.body.startswith("ERROR: Missing or invalid")

    response = wsgi_app.get('/NO_SITE/check_mk/deploy_agent.py?mode=agent')
    assert response.body.startswith("ERROR: Missing host")


def test_openapi_version(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    resp = wsgi_app.get("/NO_SITE/check_mk/api/v0/version", status=200)
    assert resp.json['site'] == cmk_version.omd_site()


def test_openapi_app_exception(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    resp = wsgi_app.get("/NO_SITE/check_mk/api/v0/version?fail=1", status=500)
    assert 'detail' in resp.json
    assert 'title' in resp.json
    # TODO: Check CrashReport storage


def test_openapi_missing_folder(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    wsgi_app.get("/NO_SITE/check_mk/api/v0/objects/folder/asdf" + uuid.uuid4().hex, status=404)


def test_openapi_hosts(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    resp = wsgi_app.call_method(
        'post',
        base + "/collections/host",
        params='{"hostname": "foobar", "folder": "root"}',
        status=200,
        content_type='application/json',
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


@pytest.mark.parametrize("group_type", ['host', 'contact', 'service'])
def test_openapi_groups(
    group_type,
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    def _random_string(size):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))

    name = _random_string(10)
    alias = _random_string(10)

    group = {'name': name, 'alias': alias}

    base = "/NO_SITE/check_mk/api/v0"
    resp = wsgi_app.call_method(
        'post',
        base + "/collections/%s_group" % (group_type,),
        params=json.dumps(group),
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.follow_link(
        resp,
        'self',
        base=base,
        status=200,
    )

    group['name'] += " updated"

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


def test_openapi_folders(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    resp = wsgi_app.call_method('get', "/NO_SITE/check_mk/api/v0/collections/folder", status=200)
    assert resp.json['value'] == []

    resp = wsgi_app.call_method('post',
                                "/NO_SITE/check_mk/api/v0/collections/folder",
                                params='{"name": "new_folder", "title": "foo", "parent": null}',
                                status=200,
                                content_type='application/json')

    base = '/NO_SITE/check_mk/api/v0'

    # First test without the proper ETag, fails with 412 (precondition failed)
    wsgi_app.follow_link(resp,
                         '.../update',
                         base=base,
                         status=400,
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

    # Invoke directly for now. Ideally this should be a 2-stage step:
    #   1. fetch the resource description
    #   2. send the argument as in the specification
    wsgi_app.follow_link(resp,
                         '.../invoke;action="move"',
                         base=base,
                         status=400,
                         headers={'If-Match': resp.headers['ETag']},
                         params=json.dumps({"destination": 'root'}),
                         content_type='application/json')

    # Check that unknown folders also give a 400
    wsgi_app.follow_link(resp,
                         '.../invoke;action="move"',
                         base=base,
                         status=400,
                         headers={'If-Match': resp.headers['ETag']},
                         params=json.dumps({"destination": 'asdf'}),
                         content_type='application/json')

    # Delete all folders.
    coll = wsgi_app.get("/NO_SITE/check_mk/api/v0/collections/folder", status=200)
    for entry in coll.json['value']:
        # Fetch the new E-Tag.
        resp = wsgi_app.get("/NO_SITE/check_mk/api/v0" + entry['href'], status=200)
        # With the right ETag, the operation shall succeed
        wsgi_app.follow_link(resp,
                             '.../delete',
                             base=base,
                             status=204,
                             headers={'If-Match': resp.headers['ETag']})


@pytest.mark.skip
def test_legacy_webapi(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, password = with_automation_user
    wsgi_app.set_credentials(username, password)
    hostname = 'foobar'

    try:
        ipaddress = '127.0.0.1'
        wsgi_app.api_request(
            'add_host',
            {
                "hostname": hostname,
                "folder": 'eins/zwei',
                # Optional
                "attributes": {
                    'ipaddress': ipaddress
                },
                "create_folders": True,
                "nodes": [],
            })

        resp = wsgi_app.api_request(
            'foo_host',
            {'hostname': hostname},
        )
        assert "Unknown API action" in resp['result']
        assert resp['result_code'] == 1

        resp = wsgi_app.api_request(
            'get_host',
            {
                'hostname': hostname,
            },
            output_format='python',
        )
        assert isinstance(resp, dict), resp
        assert isinstance(resp['result'], dict), resp['result']
        assert resp['result']['hostname'] == hostname
        assert resp['result']['attributes']['ipaddress'] == ipaddress

    finally:

        def _remove(filename):
            if os.path.exists(filename):
                os.unlink(filename)

        # FIXME: Testing of delete_host can't be done until the local automation call doesn't call
        #        out to "check_mk" via subprocess anymore. In order to not break the subsequent
        #        test, we have to delete the host ourselves. This can and will actually break
        #        unit/cmk/base/test_config.py::test_get_config_file_paths_with_confd again if
        #        more files should be created by add_host in the future.

        _remove(cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/fs_cap.mk")
        _remove(cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/wato/global.mk")
        _remove(cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/wato/groups.mk")
        _remove(cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/wato/notifications.mk")
        _remove(cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/wato/tags.mk")
        _remove(cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/wato/eins/zwei/hosts.mk")


def test_cmk_run_cron(wsgi_app):
    wsgi_app.get("/NO_SITE/check_mk/run_cron.py", status=200)


def test_cmk_automation(wsgi_app):
    response = wsgi_app.get("/NO_SITE/check_mk/automation.py", status=200)
    assert response.body == "Missing secret for automation command."


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No AJAX graphs in raw edition")
def test_cmk_ajax_graph_images(wsgi_app):
    resp = wsgi_app.get("/NO_SITE/check_mk/ajax_graph_images.py", status=200)
    assert resp.body.startswith("You are not allowed")

    resp = wsgi_app.get("/NO_SITE/check_mk/ajax_graph_images.py",
                        status=200,
                        extra_environ={'REMOTE_ADDR': '127.0.0.1'})
    assert resp.body == ""


def test_options_disabled(wsgi_app):
    # Should be 403 in integration test.
    wsgi_app.options("/", status=404)
