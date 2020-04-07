#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import ast
import contextlib
import json
import os
import sys
import threading
from cookielib import CookieJar
from urllib import urlencode

import webtest

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import
import pytest  # type: ignore[import]
from werkzeug.test import create_environ

import cmk.utils.log
import cmk.utils.paths as paths
import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.plugins.userdb import htpasswd
from cmk.gui.utils import get_random_string
from cmk.gui.watolib.users import edit_users, delete_users
from cmk.gui.wsgi import make_app
from cmk.utils import store
from testlib.utils import DummyApplication

SPEC_LOCK = threading.Lock()


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
    }
    if automation:
        user[username]['attributes'].update(automation_secret=password,)
    return user


@contextlib.contextmanager
def _create_and_destroy_user(automation=False):
    contacts_mk = paths.omd_root + "/etc/check_mk/conf.d/wato/contacts.mk"
    contact_existed = os.path.exists(contacts_mk)
    _touch(paths.htpasswd_file)
    _touch(paths.omd_root + '/etc/diskspace.conf')
    _makepath(paths.var_dir + "/wato/auth")
    _makepath(config.config_dir)
    username = u'test123-' + get_random_string(size=5, from_ascii=ord('a'), to_ascii=ord('z'))
    password = u'Ischbinwischtisch'
    edit_users(_mk_user_obj(username, password, automation=automation))
    config.load_config()
    yield username, password
    delete_users([username])
    if not contact_existed:
        os.unlink(contacts_mk)


@pytest.fixture(scope='function')
def with_user(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=False) as user:
        yield user


# noinspection PyDefaultArgument
@pytest.fixture(scope='function')
def recreate_openapi_spec(mocker, _cache=[]):  # pylint: disable=dangerous-default-value
    from cmk.gui.plugins.openapi.specgen import generate
    spec_path = paths.omd_root + "/share/checkmk/web/htdocs/openapi"
    openapi_spec_dir = mocker.patch('cmk.gui.wsgi.applications.rest_api')
    openapi_spec_dir.return_value = spec_path

    if not _cache:
        with SPEC_LOCK:
            if not _cache:
                _cache.append(generate())

    spec_data = _cache[0]
    store.save_bytes_to_file(spec_path + "/checkmk.yaml", spec_data)


@pytest.fixture()
def suppress_automation_calls(mocker):
    """Stub out calls to the "automation" system

    This is needed because in order for automation calls to work, the site needs to be set up
    properly, which can't be done in an unit-test context."""
    mocker.patch("cmk.gui.watolib.automations.check_mk_automation")
    automation = mocker.patch("cmk.gui.watolib.check_mk_automation")

    mocker.patch("cmk.gui.watolib.automations.check_mk_local_automation")
    local_automation = mocker.patch("cmk.gui.watolib.check_mk_local_automation")

    yield automation, local_automation


@pytest.fixture()
def inline_local_automation_calls(mocker):
    # Only works from Python3 code.
    def call_automation(cmd, args):
        from cmk.base.automations import automations
        return automations.execute(cmd, args)

    mocker.patch("cmk.gui.watolib.automations.check_mk_automation", new=call_automation)
    mocker.patch("cmk.gui.watolib.check_mk_automation", new=call_automation)


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
    mocker.patch("os._exit")
    mocker.patch("sys.stdout.close")
    mocker.patch("sys.stdin.close")
    mocker.patch("sys.stderr.close")
    mocker.patch("cmk.utils.daemon.daemonize")
    mocker.patch("cmk.utils.daemon.closefrom")


@pytest.fixture(scope='function')
def with_automation_user(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=True) as user:
        yield user


def _makepath(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def _touch(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).touch()


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


class WebTestAppForCMK(webtest.TestApp):
    """A webtest.TestApp class with helper functions for automation user APIs"""
    def __init__(self, *args, **kw):
        super(WebTestAppForCMK, self).__init__(*args, **kw)
        self.username = None
        self.password = None

    def set_credentials(self, username, password):
        self.username = username
        self.password = password

    def call_method(self, method, url, *args, **kw):
        return getattr(self, method.lower())(url, *args, **kw)

    def follow_link(self, resp, rel, base='', **kw):
        """Follow a link description as defined in a restful-objects entity"""
        # if rel.startswith(".../"):
        #     rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
        # if rel.startswith("cmk/"):
        #     rel = rel.replace("cmk/", "urn:com.checkmk:rels/")
        link = get_link(resp.json, rel)
        return self.call_method(link.get('method', 'GET').lower(), base + link['href'], **kw)

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
        elif output_format == 'json':
            return json.loads(_resp.body)
        else:
            raise NotImplementedError("Format %s not implemented" % output_format)


@pytest.fixture(scope='function')
def wsgi_app(monkeypatch, recreate_openapi_spec):
    monkeypatch.setenv("OMD_SITE", "NO_SITE")
    store.makedirs(paths.omd_root + '/var/check_mk/web')
    store.makedirs(paths.omd_root + '/var/check_mk/php-api')
    store.makedirs(paths.omd_root + '/var/check_mk/wato/php-api')
    store.makedirs(paths.omd_root + '/var/log')
    store.makedirs(paths.omd_root + '/tmp/check_mk')
    wsgi_callable = make_app()
    cookies = CookieJar()
    return WebTestAppForCMK(wsgi_callable, cookiejar=cookies)  # type: WebTestAppForCMK
