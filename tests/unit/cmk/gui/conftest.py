#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from __future__ import annotations

import ast
import contextlib
import json
import threading
import urllib.parse
from contextlib import contextmanager
from http.cookiejar import CookieJar
from typing import Any, Callable, ContextManager, Dict, Iterator, Literal, NamedTuple, Optional

import pytest
import webtest  # type: ignore[import]

# TODO: Change to pytest.MonkeyPatch. It will be available in future pytest releases.
from _pytest.monkeypatch import MonkeyPatch
from mock import MagicMock

from tests.testlib.users import create_and_destroy_user

import cmk.utils.log
from cmk.utils.type_defs import UserId

import cmk.gui.config as config_module
import cmk.gui.login as login
import cmk.gui.watolib.activate_changes as activate_changes
from cmk.gui import main_modules, watolib
from cmk.gui.globals import config
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.json import patch_json
from cmk.gui.utils.logged_in import SuperUserContext, UserContext
from cmk.gui.utils.script_helpers import application_and_request_context, session_wsgi_app
from cmk.gui.watolib import hosts_and_folders, search

SPEC_LOCK = threading.Lock()


class RemoteAutomation(NamedTuple):
    automation: MagicMock
    responses: Any


HTTPMethod = Literal[
    "get",
    "put",
    "post",
    "delete",
    "GET",
    "PUT",
    "POST",
    "DELETE",
]  # yapf: disable


@pytest.fixture()
def request_context() -> Iterator[None]:
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    with application_and_request_context():
        yield


@pytest.fixture()
def monkeypatch(monkeypatch: MonkeyPatch, request_context: None) -> Iterator[MonkeyPatch]:
    """Makes patch/undo of request globals possible

    In the GUI we often use the monkeypatch for patching request globals (e.g.
    cmk.gui.globals.config). To be able to undo all these patches, we need to be within the request
    context while monkeypatch.undo is running. However, with the default "monkeypatch" fixture the
    undo would be executed after leaving the application and request context.

    What we do here is to override the default monkeypatch fixture of pytest for the GUI tests:
    See also: https://github.com/pytest-dev/pytest/blob/main/src/_pytest/monkeypatch.py.

    The drawback here may be that we create some unnecessary application / request context objects
    for some tests. If you have an idea for a cleaner approach, let me know.
    """
    with monkeypatch.context() as m:
        yield m


@pytest.fixture()
def load_config(request_context: None) -> Iterator[None]:
    old_root_log_level = cmk.utils.log.logger.getEffectiveLevel()
    config_module.initialize()
    yield
    cmk.utils.log.logger.setLevel(old_root_log_level)


@pytest.fixture(scope="session", autouse=True)
def load_plugins() -> None:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plugin loading: {errors}")


@pytest.fixture(name="patch_json", autouse=True)
def fixture_patch_json() -> Iterator[None]:
    with patch_json(json):
        yield


@pytest.fixture()
def with_user(request_context: None, load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="user") as user:
        yield user


@pytest.fixture()
def with_user_login(with_user: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = with_user[0]
    with login.UserSessionContext(user_id):
        yield user_id


@pytest.fixture()
def with_admin(request_context: None, load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="admin") as user:
        yield user


@pytest.fixture()
def with_admin_login(with_admin: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = with_admin[0]
    with login.UserSessionContext(user_id):
        yield user_id


@pytest.fixture()
def suppress_remote_automation_calls(mocker: MagicMock) -> Iterator[RemoteAutomation]:
    """Stub out calls to the remote automation system
    This is needed because in order for remote automation calls to work, the site needs to be set up
    properly, which can't be done in an unit-test context."""
    remote_automation = mocker.patch("cmk.gui.watolib.automations.do_remote_automation")
    mocker.patch("cmk.gui.watolib.do_remote_automation", new=remote_automation)
    yield RemoteAutomation(
        automation=remote_automation,
        responses=None,
    )


@pytest.fixture()
def make_html_object_explode(mocker: MagicMock) -> None:
    class HtmlExploder:
        def __init__(self, *args, **kw):
            raise NotImplementedError("Tried to instantiate html")

    mocker.patch("cmk.gui.htmllib.html", new=HtmlExploder)


@pytest.fixture()
def inline_background_jobs(mocker: MagicMock) -> None:
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


@pytest.fixture()
def with_automation_user(request_context: None, load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="admin") as user:
        yield user


def get_link(resp: dict, rel: str):
    for link in resp.get("links", []):
        if link["rel"].startswith(rel):
            return link
    if "result" in resp:
        for link in resp["result"].get("links", []):
            if link["rel"].startswith(rel):
                return link
    for member in resp.get("members", {}).values():
        if member["memberType"] == "action":
            for link in member["links"]:
                if link["rel"].startswith(rel):
                    return link
    raise KeyError("%r not found" % (rel,))


def _expand_rel(rel: str) -> str:
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
    if rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/")
    return rel


class WebTestAppForCMK(webtest.TestApp):
    """A webtest.TestApp class with helper functions for automation user APIs"""

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    def set_credentials(self, username, password) -> None:
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
            if "body_params" in link and link["body_params"]:
                params["params"] = json.dumps(link["body_params"])
                params["content_type"] = "application/json"
            resp = self.call_method(link["method"], link["href"], **params)
        return resp

    def api_request(self, action, request, output_format="json", **kw):
        if self.username is None or self.password is None:
            raise RuntimeError("Not logged in.")
        qs = urllib.parse.urlencode(
            [
                ("_username", self.username),
                ("_secret", self.password),
                ("request_format", output_format),
                ("action", action),
            ]
        )
        if output_format == "python":
            request = repr(request)
        elif output_format == "json":
            request = json.dumps(request)
        else:
            raise NotImplementedError("Format %s not implemented" % output_format)

        _resp = self.call_method(
            "post",
            "/NO_SITE/check_mk/webapi.py?" + qs,
            params={"request": request, "_username": self.username, "_secret": self.password},
            **kw,
        )
        assert "Invalid automation secret for user" not in _resp.body
        assert "API is only available for automation users" not in _resp.body

        if output_format == "python":
            return ast.literal_eval(_resp.body)
        if output_format == "json":
            return json.loads(_resp.body)
        raise NotImplementedError("Format %s not implemented" % output_format)

    @contextmanager
    def set_config(self, **kwargs: Any) -> Iterator[None]:
        """Patch the GUI config for the current test

        In normal tests, if you want to patch the GUI config, you can simply monkeypatch the
        attribute of your choice. But with the webtest, the config is read during the request
        handling in the test. This needs a special handling.
        """

        def _set_config():
            for key, val in kwargs.items():
                setattr(config, key, val)

        try:
            config_module.register_post_config_load_hook(_set_config)
            yield
        finally:
            config_module._post_config_load_hooks.remove(_set_config)

    def login(self, username: str, password: str) -> WebTestAppForCMK:
        self.username = username
        login = self.get("/NO_SITE/check_mk/login.py")
        login.form["_username"] = username
        login.form["_password"] = password
        resp = login.form.submit("_login", index=1)
        assert "Invalid credentials." not in resp.text
        return self


def _make_webtest(debug):
    cookies = CookieJar()
    return WebTestAppForCMK(session_wsgi_app(debug), cookiejar=cookies)


@pytest.fixture()
def wsgi_app(monkeypatch, request_context):
    return _make_webtest(debug=True)


@pytest.fixture()
def wsgi_app_debug_off(monkeypatch):
    return _make_webtest(debug=False)


@pytest.fixture(autouse=True)
def avoid_search_index_update_background(monkeypatch):
    monkeypatch.setattr(
        search,
        "update_index_background",
        lambda _change_action_name: ...,
    )


@pytest.fixture()
def logged_in_wsgi_app(wsgi_app, with_user):
    return wsgi_app.login(with_user[0], with_user[1])


@pytest.fixture()
def logged_in_admin_wsgi_app(wsgi_app, with_admin):
    return wsgi_app.login(with_admin[0], with_admin[1])


@pytest.fixture()
def with_groups(request_context, with_admin_login, suppress_remote_automation_calls):
    watolib.add_group("windows", "host", {"alias": "windows"})
    watolib.add_group("routers", "service", {"alias": "routers"})
    watolib.add_group("admins", "contact", {"alias": "admins"})
    yield
    watolib.delete_group("windows", "host")
    watolib.delete_group("routers", "service")
    watolib.delete_group("admins", "contact")


@pytest.fixture()
def with_host(
    monkeypatch: pytest.MonkeyPatch,
    request_context,
    with_admin_login,
):
    hostnames = ["heute", "example.com"]
    hosts_and_folders.CREFolder.root_folder().create_hosts(
        [(hostname, {}, None) for hostname in hostnames]
    )
    yield hostnames
    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.delete_hosts",
        lambda *args, **kwargs: None,
    )
    hosts_and_folders.CREFolder.root_folder().delete_hosts(hostnames)


@pytest.fixture(autouse=True)
def mock__add_extensions_for_license_usage(monkeypatch):
    monkeypatch.setattr(activate_changes, "_add_extensions_for_license_usage", lambda: None)


@pytest.fixture
def run_as_user() -> Callable[[UserId], ContextManager[None]]:
    """Fixture to run parts of test-code as another user

    Examples:

        def test_function(run_as_user):
            print("Run as Nobody")
            with run_as_user(UserID("egon")):
                 print("Run as 'egon'")
            print("Run again as Nobody")

    """

    @contextlib.contextmanager
    def _run_as_user(user_id: UserId) -> Iterator[None]:
        cmk.gui.config.load_config()
        with UserContext(user_id):
            yield None

    return _run_as_user


@pytest.fixture
def run_as_superuser() -> Callable[[], ContextManager[None]]:
    """Fixture to run parts of test-code as the superuser

    Examples:

        def test_function(run_as_superuser):
            print("Run as Nobody")
            with run_as_superuser():
                 print("Run as Superuser")
            print("Run again as Nobody")

    """

    @contextlib.contextmanager
    def _run_as_superuser() -> Iterator[None]:
        cmk.gui.config.load_config()
        with SuperUserContext():
            yield None

    return _run_as_superuser
