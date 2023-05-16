#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import ast
import contextlib
import json
import shutil
import threading
import urllib.parse
from contextlib import contextmanager
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, NamedTuple, Literal, Optional, Dict, Iterator
from functools import lru_cache

import pytest  # type: ignore[import]
import webtest  # type: ignore[import]
from mock import MagicMock
from werkzeug.test import create_environ

from cmk.gui import watolib
from testlib.utils import DummyApplication

import cmk.utils.log
import cmk.utils.paths as paths

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
import cmk.gui.login as login
from cmk.gui.display_options import DisplayOptions
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.http import Request
from cmk.gui.utils import get_random_string
from cmk.gui.watolib import search, hosts_and_folders
from cmk.gui.watolib.users import delete_users, edit_users
from cmk.gui.wsgi import make_app
import cmk.gui.watolib.activate_changes as activate_changes

SPEC_LOCK = threading.Lock()

Automation = NamedTuple("Automation", [
    ("automation", MagicMock),
    ("local_automation", MagicMock),
    ("remote_automation", MagicMock),
    ("responses", Any),
])

HTTPMethod = Literal[
    "get", "put", "post", "delete",
    "GET", "PUT", "POST", "DELETE",
]  # yapf: disable


@pytest.fixture(scope='function')
def register_builtin_html():
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    environ = create_environ()
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ)), display_options=DisplayOptions()):
        yield


@pytest.fixture(scope='module')
def module_wide_request_context():
    # This one is kind of an hack because some other test-fixtures touch the user object AFTER the
    # request context has already ended. If we increase our scope this won't matter, but it is of
    # course wrong. These other fixtures have to be fixed.
    environ = create_environ()
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ)), display_options=DisplayOptions()):
        yield


@pytest.fixture()
def load_config(register_builtin_html):
    old_root_log_level = cmk.utils.log.logger.getEffectiveLevel()
    config.initialize()
    yield
    cmk.utils.log.logger.setLevel(old_root_log_level)


@pytest.fixture()
def load_plugins(register_builtin_html, monkeypatch, tmp_path):
    import cmk.gui.modules as modules
    config_dir = tmp_path / "var/check_mk/web"
    config_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "config_dir", "%s" % config_dir)
    monkeypatch.setattr(config, "roles", {'user': {}, 'admin': {}, 'guest': {}})
    modules.load_all_plugins()


def _mk_user_obj(username, password, automation=False):
    # This dramatically improves the performance of the unit tests using this in fixtures
    precomputed_hashes = {
        "Ischbinwischtisch": '$5$rounds=535000$mn3ra3ny1cbHVGsW$5kiJmJcgQ6Iwd1R.i4.kGAQcMF.7zbCt0BOdRG8Mn.9',
    }

    if password not in precomputed_hashes:
        raise ValueError("Add your hash to precomputed_hashes")

    user = {
        username: {
            'attributes': {
                'alias': username,
                'email': 'admin@example.com',
                'password': precomputed_hashes[password],
                'notification_method': 'email',
                'roles': ['admin'],
                'serial': 0
            },
            'is_new_user': True,
        }
    }  # type: dict
    if automation:
        user[username]['attributes'].update(automation_secret=password,)
    return user


@contextlib.contextmanager
def _create_and_destroy_user(automation=False, role="user"):
    username = u'test123-' + get_random_string(size=5, from_ascii=ord('a'), to_ascii=ord('z'))
    password = u'Ischbinwischtisch'
    edit_users(_mk_user_obj(username, password, automation=automation))
    config.load_config()

    profile_path = Path(paths.omd_root, "var", "check_mk", "web", username)
    profile_path.joinpath('cached_profile.mk').write_text(
        str(
            repr({
                'alias': u'Test user',
                'contactgroups': ['all'],
                'disable_notifications': {},
                'email': u'test_user_%s@checkmk.com' % username,
                'fallback_contact': False,
                'force_authuser': False,
                'locked': False,
                'language': 'de',
                'pager': '',
                'roles': [role],
                'start_url': None,
                'ui_theme': 'modern-dark',
            })))

    yield username, password

    delete_users([username])

    # User directories are not deleted by WATO by default. Clean it up here!
    shutil.rmtree(str(profile_path))


@pytest.fixture(scope='function')
def with_user(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=False) as user:
        yield user


@pytest.fixture(scope='function')
def with_user_login(with_user):
    user_id = with_user[0]
    with login.UserSessionContext(user_id):
        yield user_id


@pytest.fixture(scope='function')
def with_admin(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=False, role="admin") as user:
        yield user


@pytest.fixture(scope='function')
def with_admin_login(with_admin):
    user_id = with_admin[0]
    with login.UserSessionContext(user_id):
        yield user_id


@pytest.fixture()
def suppress_automation_calls(mocker):
    """Stub out calls to the "automation" system

    This is needed because in order for automation calls to work, the site needs to be set up
    properly, which can't be done in an unit-test context."""
    automation = mocker.patch("cmk.gui.watolib.automations.check_mk_automation")
    mocker.patch("cmk.gui.watolib.check_mk_automation", new=automation)

    local_automation = mocker.patch("cmk.gui.watolib.automations.check_mk_local_automation")
    mocker.patch("cmk.gui.watolib.check_mk_local_automation", new=local_automation)

    remote_automation = mocker.patch("cmk.gui.watolib.automations.do_remote_automation")
    mocker.patch("cmk.gui.watolib.do_remote_automation", new=remote_automation)

    yield Automation(automation=automation,
                     local_automation=local_automation,
                     remote_automation=remote_automation,
                     responses=None)


@pytest.fixture()
def inline_local_automation_calls(mocker):
    # Only works from Python3 code.
    def call_automation(cmd, args):
        from cmk.base.automations import automations
        return automations.execute(cmd, args)

    mocker.patch("cmk.gui.watolib.automations.check_mk_automation", new=call_automation)
    mocker.patch("cmk.gui.watolib.check_mk_automation", new=call_automation)


@pytest.fixture()
def make_html_object_explode(mocker):
    class HtmlExploder:
        def __init__(self, *args, **kw):
            raise NotImplementedError("Tried to instantiate html")

    mocker.patch("cmk.gui.htmllib.html", new=HtmlExploder)


@pytest.fixture()
def inline_background_jobs(mocker):
    """Prevent multiprocess.Process to spin off a new process

    This will run the code (non-concurrently, blocking) in the main execution path.
    """
    # Process.start spins of the new process. We tell it to just run the job instead.
    mocker.patch("multiprocessing.Process.start", new=lambda self: self.run())
    # We stub out everything preventing smooth execution.
    mocker.patch("multiprocessing.Process.join")
    mocker.patch("sys.exit")
    mocker.patch("cmk.gui.watolib.ActivateChangesSite._detach_from_parent")
    mocker.patch("cmk.gui.watolib.ActivateChangesSite._close_apache_fds")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._detach_from_parent")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._open_stdout_and_stderr")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._register_signal_handlers")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._register_signal_handlers")
    mocker.patch("cmk.gui.background_job.BackgroundJob._exit")
    mocker.patch("cmk.utils.daemon.daemonize")
    mocker.patch("cmk.utils.daemon.closefrom")


@pytest.fixture(scope='function')
def with_automation_user(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=True) as user:
        yield user


def get_link(resp, rel: str):
    for link in resp.get('links', []):
        if link['rel'].startswith(rel):
            return link
    if 'result' in resp:
        for link in resp['result'].get('links', []):
            if link['rel'].startswith(rel):
                return link
    for member in resp.get('members', {}).values():
        if member['memberType'] == 'action':
            for link in member['links']:
                if link['rel'].startswith(rel):
                    return link
    raise KeyError("%r not found" % (rel,))


def _expand_rel(rel):
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
    if rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/")
    return rel


class WebTestAppForCMK(webtest.TestApp):
    """A webtest.TestApp class with helper functions for automation user APIs"""
    def __init__(self, *args, **kw):
        super(WebTestAppForCMK, self).__init__(*args, **kw)
        self.username = None
        self.password = None

    def set_credentials(self, username, password):
        self.username = username
        self.password = password

    def call_method(self, method: HTTPMethod, url, *args, **kw) -> webtest.TestResponse:
        print(method, url, args, kw)
        return getattr(self, method.lower())(url, *args, **kw)

    def has_link(self, resp: webtest.TestResponse, rel) -> bool:
        if resp.status_code == 204:
            return False
        try:
            _ = get_link(resp.json, _expand_rel(rel))
            return True
        except KeyError:
            return False

    def follow_link(
        self,
        resp: webtest.TestResponse,
        rel,
        json_data: Optional[Dict[str, Any]] = None,
        **kw,
    ) -> webtest.TestResponse:
        """Follow a link description as defined in a restful-objects entity"""
        params = dict(kw)
        if resp.status.startswith("2") and resp.content_type.endswith("json"):
            if json_data is None:
                json_data = resp.json
            link = get_link(json_data, _expand_rel(rel))
            if 'body_params' in link and link['body_params']:
                params['params'] = json.dumps(link['body_params'])
                params['content_type'] = 'application/json'
            resp = self.call_method(link['method'], link['href'], **params)
        return resp

    def api_request(self, action, request, output_format='json', **kw):
        if self.username is None or self.password is None:
            raise RuntimeError("Not logged in.")
        qs = urllib.parse.urlencode([
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

        _resp = self.call_method('post',
                                 '/NO_SITE/check_mk/webapi.py?' + qs,
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
        if output_format == 'json':
            return json.loads(_resp.body)
        raise NotImplementedError("Format %s not implemented" % output_format)

    @contextmanager
    def set_config(self, **kwargs: Dict[str, Any]) -> Iterator[None]:
        """Patch the GUI config for the current test

        In normal tests, if you want to patch the GUI config, you can simply monkeypatch the
        attribute of your choice. But with the webtest, the config is read during the request
        handling in the test. This needs a special handling.
        """
        def _set_config():
            for key, val in kwargs.items():
                setattr(config, key, val)

        config.register_post_config_load_hook(_set_config)
        yield
        config._post_config_load_hooks.remove(_set_config)


@lru_cache
def _session_wsgi_callable(debug):
    return make_app(debug=debug)


def _make_webtest(debug):
    cookies = CookieJar()
    return WebTestAppForCMK(_session_wsgi_callable(debug), cookiejar=cookies)


@pytest.fixture(scope='function')
def wsgi_app(monkeypatch):
    return _make_webtest(debug=True)


@pytest.fixture(scope='function')
def wsgi_app_debug_off(monkeypatch):
    return _make_webtest(debug=False)


@pytest.fixture(scope='function', autouse=True)
def avoid_search_index_update_background(monkeypatch):
    monkeypatch.setattr(
        search,
        'update_index_background',
        lambda _change_action_name:...,
    )


@pytest.fixture(scope='function')
def logged_in_wsgi_app(wsgi_app, with_user):
    username, password = with_user
    wsgi_app.username = username
    login = wsgi_app.get('/NO_SITE/check_mk/login.py')
    login.form['_username'] = username
    login.form['_password'] = password
    resp = login.form.submit('_login', index=1)
    assert "Invalid credentials." not in resp.text
    return wsgi_app


@pytest.fixture(scope='function')
def with_groups(
    monkeypatch,
    module_wide_request_context,
    with_user_login,
    suppress_automation_calls,
):
    watolib.add_group('windows', 'host', {'alias': 'windows'})
    watolib.add_group('routers', 'service', {'alias': 'routers'})
    watolib.add_group('admins', 'contact', {'alias': 'admins'})
    yield
    watolib.delete_group('windows', 'host')
    watolib.delete_group('routers', 'service')
    monkeypatch.setattr(cmk.gui.watolib.mkeventd, "_get_rule_stats_from_ec", lambda: {})
    watolib.delete_group('admins', 'contact')


@pytest.fixture(scope='function')
def with_host(module_wide_request_context, with_user_login, suppress_automation_calls):
    hostnames = ["heute", "example.com"]
    hosts_and_folders.CREFolder.root_folder().create_hosts([
        (hostname, {}, None) for hostname in hostnames
    ])
    yield hostnames
    hosts_and_folders.CREFolder.root_folder().delete_hosts(hostnames)


@pytest.fixture(autouse=True)
def mock__add_extensions_for_license_usage(monkeypatch):
    monkeypatch.setattr(activate_changes, "_add_extensions_for_license_usage", lambda: None)
