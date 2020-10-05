#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import ast
import contextlib
import json
import shutil
import threading
import urllib.parse
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, NamedTuple, Literal

import pytest  # type: ignore[import]
import webtest  # type: ignore[import]
from mock import MagicMock
from six import ensure_str
from werkzeug.test import create_environ

from testlib.utils import DummyApplication

import cmk.utils.log
import cmk.utils.paths as paths
from cmk.utils import store

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
import cmk.gui.login as login
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.http import Request
from cmk.gui.plugins.userdb import htpasswd
from cmk.gui.utils import get_random_string
from cmk.gui.watolib.users import delete_users, edit_users
from cmk.gui.wsgi import make_app

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
            RequestContext(htmllib.html(Request(environ))):
        yield


@pytest.fixture(scope='module')
def module_wide_request_context():
    # This one is kind of an hack because some other test-fixtures touch the user object AFTER the
    # request context has already ended. If we increase our scope this won't matter, but it is of
    # course wrong. These other fixtures have to be fixed.
    environ = create_environ()
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ))):
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
    modules.load_all_plugins()


def _mk_user_obj(username, password, automation=False):
    user = {
        username: {
            'attributes': {
                'alias': username,
                'email': 'admin@example.com',
                'password': htpasswd.hash_password(password),
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
                'email': u'test_user_%s@tribe29.com' % username,
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
    login.login(user_id)
    yield user_id
    config.clear_user_login()


@pytest.fixture(scope='function')
def with_admin(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=False, role="admin") as user:
        yield user


@pytest.fixture(scope='function')
def with_admin_login(with_admin):
    user_id = with_admin[0]
    login.login(user_id)
    yield user_id
    config.clear_user_login()


# noinspection PyDefaultArgument
@pytest.fixture(scope='function')
def recreate_openapi_spec(mocker, _cache=[]):  # pylint: disable=dangerous-default-value
    from cmk.gui.openapi import generate
    spec_path = paths.omd_root + "/share/checkmk/web/htdocs/openapi"
    openapi_spec_dir = mocker.patch('cmk.gui.wsgi.applications.rest_api')
    openapi_spec_dir.return_value = spec_path

    if not _cache:
        with SPEC_LOCK:
            if not _cache:
                _cache.append(generate())

    spec_data = ensure_str(_cache[0])
    store.makedirs(spec_path)
    store.save_text_to_file(spec_path + "/checkmk.yaml", spec_data)


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


def get_link(resp, rel):
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
        return getattr(self, method.lower())(url, *args, **kw)

    def has_link(self, resp: webtest.TestResponse, rel) -> bool:
        if resp.status_code == 204:
            return False
        try:
            _ = get_link(resp.json, _expand_rel(rel))
            return True
        except KeyError:
            return False

    def follow_link(self, resp: webtest.TestResponse, rel, base='', **kw) -> webtest.TestResponse:
        """Follow a link description as defined in a restful-objects entity"""
        rel = _expand_rel(rel)
        if resp.status.startswith("2") and resp.content_type.endswith("json"):
            link = get_link(resp.json, rel)
            return self.call_method(link.get('method', 'GET').lower(), base + link['href'], **kw)
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


def _make_webtest(debug):
    wsgi_callable = make_app(debug=debug)
    cookies = CookieJar()
    return WebTestAppForCMK(wsgi_callable, cookiejar=cookies)


@pytest.fixture(scope='function')
def wsgi_app(monkeypatch):
    return _make_webtest(debug=True)


@pytest.fixture(scope='function')
def wsgi_app_debug_off(monkeypatch):
    return _make_webtest(debug=False)
