#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import typing

import pytest  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.version as cmk_version

if typing.TYPE_CHECKING:
    import webtest  # type: ignore[import] # pylint: disable=unused-import


def test_profiling(wsgi_app, mocker):
    var_dir = cmk.utils.paths.var_dir
    assert not os.path.exists(var_dir + "/multisite.py")
    assert not os.path.exists(var_dir + "/multisite.profile")
    assert not os.path.exists(var_dir + "/multisite.cachegrind")

    config = mocker.patch("cmk.gui.config")
    config.profile = True

    _ = wsgi_app.get('/NO_SITE/check_mk/login.py')

    assert os.path.exists(var_dir + "/multisite.py")
    assert os.path.exists(var_dir + "/multisite.profile")
    assert os.path.exists(var_dir + "/multisite.cachegrind")


def test_normal_auth(wsgi_app, with_user):
    username, password = with_user
    login: 'webtest.TestResponse' = wsgi_app.get('/NO_SITE/check_mk/login.py')
    login.form['_username'] = username
    login.form['_password'] = password
    resp = login.form.submit('_login', index=1)

    assert "Invalid credentials." not in resp.text


def test_openapi_version(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    resp = wsgi_app.get("/NO_SITE/check_mk/api/v0/version", status=200)
    assert resp.json['site'] == cmk_version.omd_site()


def test_openapi_app_exception(wsgi_app_debug_off, with_automation_user):
    wsgi_app = wsgi_app_debug_off
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    resp = wsgi_app.get("/NO_SITE/check_mk/api/v0/version?fail=1", status=500)
    assert 'detail' in resp.json
    assert 'title' in resp.json
    assert 'crash_report' in resp.json
    assert 'check_mk' in resp.json['crash_report']['href']
    assert 'crash_id' in resp.json


@pytest.mark.skip
def test_legacy_webapi(wsgi_app, with_automation_user):
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
    assert response.text == "Missing secret for automation command."


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No AJAX graphs in raw edition")
def test_cmk_ajax_graph_images(wsgi_app):
    resp = wsgi_app.get("/NO_SITE/check_mk/ajax_graph_images.py", status=200)
    assert resp.text.startswith("You are not allowed")

    resp = wsgi_app.get("/NO_SITE/check_mk/ajax_graph_images.py",
                        status=200,
                        extra_environ={'REMOTE_ADDR': '127.0.0.1'})
    assert resp.text == ""


def test_options_disabled(wsgi_app):
    # Should be 403 in integration test.
    wsgi_app.options("/", status=404)
