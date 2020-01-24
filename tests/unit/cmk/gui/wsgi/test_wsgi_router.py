import ast
import json
import os
from cookielib import CookieJar
from urllib import urlencode

import pytest
import webtest

import cmk
from cmk.utils import store
from cmk.gui.wsgi import make_app

# pylint: disable=redefined-outer-name


class WebTestAppForCMK(webtest.TestApp):
    """A webtest.TestApp class with helper functions for automation user APIs"""
    def __init__(self, *args, **kw):
        super(WebTestAppForCMK, self).__init__(*args, **kw)
        self.username = None
        self.password = None

    def set_credentials(self, username, password):
        self.username = username
        self.password = password

    def api_request(self, action, request, output_format='json', **kw):
        if self.username is None or self.password is None:
            raise RuntimeError("Not logged in.")
        qs = urlencode([
            ('_username', self.username),
            ('_secret', self.password),
            ('request_format', output_format),
            ('action', action),
        ])
        if output_format == 'python':
            request = repr(request)
        elif output_format == 'json':
            request = json.dumps(request)
        else:
            raise NotImplementedError("Format %s not implemented" % output_format)

        _resp = self.post('/NO_SITE/check_mk/webapi.py?' + qs,
                          params={
                              'request': request,
                              '_username': self.username,
                              '_secret': self.password
                          },
                          **kw)
        assert "Invalid automation secret for user" not in _resp.body
        assert "API is only available for automation users" not in _resp.body

        if output_format == 'python':
            return ast.literal_eval(_resp.body)
        elif output_format == 'json':
            return json.loads(_resp.body)
        else:
            raise NotImplementedError("Format %s not implemented" % output_format)


@pytest.fixture(scope='function')
def wsgi_app(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "NO_SITE")
    store.makedirs(cmk.utils.paths.omd_root + '/var/check_mk/web')
    store.makedirs(cmk.utils.paths.omd_root + '/var/check_mk/php-api')
    store.makedirs(cmk.utils.paths.omd_root + '/var/check_mk/wato/php-api')
    store.makedirs(cmk.utils.paths.omd_root + '/tmp/check_mk')
    wsgi_callable = make_app()
    cookies = CookieJar()
    return WebTestAppForCMK(wsgi_callable, cookiejar=cookies)


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


@pytest.mark.skipif(cmk.is_raw_edition(), reason="No agent deployment in raw edition")
def test_deploy_agent(wsgi_app):
    response = wsgi_app.get('/NO_SITE/check_mk/deploy_agent.py')
    assert response.body.startswith("Missing or invalid")

    response = wsgi_app.get('/NO_SITE/check_mk/deploy_agent.py?mode=agent')
    assert response.body.startswith("Missing host")


def test_openapi_app(
    wsgi_app,  # type: WebTestAppForCMK
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    wsgi_app.get("/NO_SITE/check_mk/api/v0/version")


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


def test_cmk_pnp_template(wsgi_app):
    wsgi_app.get("/NO_SITE/check_mk/pnp_template.py", status=200)


def test_cmk_automation(wsgi_app):
    response = wsgi_app.get("/NO_SITE/check_mk/automation.py", status=200)
    assert response.body == "Missing secret for automation command."


@pytest.mark.skipif(cmk.is_raw_edition(), reason="No AJAX graphs in raw edition")
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
