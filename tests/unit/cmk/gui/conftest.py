#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from __future__ import annotations

import json
import threading
import typing
import urllib.parse
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from http.cookiejar import CookieJar
from typing import Any, ContextManager, Literal, NamedTuple
from unittest import mock
from unittest.mock import MagicMock

import pytest
import webtest  # type: ignore[import]
from flask import Flask
from mypy_extensions import KwArg
from pytest_mock import MockerFixture
from werkzeug.test import create_environ

from tests.testlib.plugin_registry import reset_registries
from tests.testlib.rest_api_client import (
    ClientRegistry,
    expand_rel,
    get_client_registry,
    get_link,
    RequestHandler,
    Response,
    RestApiClient,
)
from tests.testlib.users import create_and_destroy_user

import cmk.utils.log
from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.plugin_registry import Registry
from cmk.utils.user import UserId

from cmk.automations.results import DeleteHostsResult

import cmk.gui.config as config_module
import cmk.gui.login as login
import cmk.gui.watolib.activate_changes as activate_changes
import cmk.gui.watolib.groups as groups
import cmk.gui.watolib.mkeventd as mkeventd
import cmk.gui.watolib.password_store
from cmk.gui import hooks, http, main_modules, userdb
from cmk.gui.config import active_config
from cmk.gui.dashboard import dashlet_registry
from cmk.gui.livestatus_utils.testing import mock_livestatus
from cmk.gui.permissions import permission_registry, permission_section_registry
from cmk.gui.session import session, SuperUserContext, UserContext
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb.session import load_session_infos
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.json import patch_json
from cmk.gui.utils.script_helpers import session_wsgi_app
from cmk.gui.watolib.hosts_and_folders import folder_tree

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
]  # fmt: off


@pytest.fixture
def mock_password_file_regeneration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.password_store,
        cmk.gui.watolib.password_store.update_passwords_merged_file.__name__,
        lambda: None,
    )


@pytest.fixture(autouse=True)
def deactivate_search_index_building_at_requenst_end(mocker: MockerFixture) -> None:
    mocker.patch(
        "cmk.gui.watolib.search.updates_requested",
        return_value=False,
    )


@pytest.fixture(autouse=True)
def gui_cleanup_after_test(
    request_context: None,
    deactivate_search_index_building_at_requenst_end: None,
) -> Iterator[None]:
    yield

    # In case some tests use @request_memoize but don't use the request context, we'll emit the
    # clear event after each request.
    hooks.call("request-end")


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    with flask_app.test_request_context():
        flask_app.preprocess_request()
        yield
        flask_app.process_response(http.Response())


@pytest.fixture(name="mock_livestatus")
def fixture_mock_livestatus() -> Iterator[MockLiveStatusConnection]:
    """UI specific override of the global mock_livestatus fixture"""
    with mock_livestatus() as mock_live:
        yield mock_live


@pytest.fixture()
def load_config(request_context: None) -> Iterator[None]:
    old_root_log_level = cmk.utils.log.logger.getEffectiveLevel()
    config_module.initialize()
    yield
    cmk.utils.log.logger.setLevel(old_root_log_level)


SetConfig = Callable[[KwArg(Any)], ContextManager[None]]


@pytest.fixture(name="set_config")
def set_config_fixture() -> SetConfig:
    return set_config


@contextmanager
def set_config(**kwargs: Any) -> Iterator[None]:
    """Patch the config

    This works even in WSGI tests, where the config is (re-)loaded by the app itself,
    through the registered callback.
    """

    def _set_config():
        for key, val in kwargs.items():
            setattr(active_config, key, val)

    def fake_load_single_global_wato_setting(
        varname: str,
        deflt: typing.Any | None = None,
    ) -> typing.Any:
        return kwargs.get(varname, deflt)

    try:
        config_module.register_post_config_load_hook(_set_config)
        if kwargs:
            # NOTE: patch.multiple doesn't want to receive an empty kwargs dict and will crash.
            with (
                mock.patch.multiple(active_config, **kwargs),
                mock.patch(
                    "cmk.gui.wsgi.applications.utils.load_single_global_wato_setting",
                    new=fake_load_single_global_wato_setting,
                ),
            ):
                yield
        else:
            yield
    finally:
        config_module._post_config_load_hooks.remove(_set_config)


@pytest.fixture(scope="session", autouse=True)
def load_plugins() -> None:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


@pytest.fixture()
def ui_context(load_plugins: None, load_config: None) -> Iterator[None]:
    """Some helper fixture to provide a initialized UI context to tests outside of tests/unit/cmk/gui"""
    yield


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
    user_id = UserId(with_user[0])
    with login.TransactionIdContext(user_id):
        yield user_id


@pytest.fixture()
def with_admin(request_context: None, load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="admin") as user:
        yield user


@pytest.fixture()
def with_admin_login(with_admin: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = with_admin[0]
    with login.TransactionIdContext(user_id):
        yield user_id


@pytest.fixture()
def suppress_remote_automation_calls(mocker: MagicMock) -> Iterator[RemoteAutomation]:
    """Stub out calls to the remote automation system
    This is needed because in order for remote automation calls to work, the site needs to be set up
    properly, which can't be done in an unit-test context."""
    remote_automation = mocker.patch("cmk.gui.watolib.automations.do_remote_automation")
    mocker.patch("cmk.gui.watolib.automations.do_remote_automation", new=remote_automation)
    yield RemoteAutomation(
        automation=remote_automation,
        responses=None,
    )


@pytest.fixture()
def make_html_object_explode(mocker: MagicMock) -> None:
    class HtmlExploder:
        def __init__(self, *args: object, **kw: object) -> None:
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
    mocker.patch("cmk.gui.background_job.BackgroundProcess._detach_from_parent")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._open_stdout_and_stderr")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._register_signal_handlers")
    mocker.patch("cmk.gui.background_job.BackgroundProcess._register_signal_handlers")
    mocker.patch("cmk.gui.background_job.BackgroundJob._exit")
    mocker.patch("cmk.utils.daemon.daemonize")
    mocker.patch("cmk.utils.daemon.closefrom")


@pytest.fixture(name="suppress_bake_agents_in_background")
def fixture_suppress_bake_agents_in_background(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.bakery.try_bake_agents_for_hosts",
        side_effect=lambda *args, **kw: None,
    )


# TODO: The list of registries is not complete. It would be better to selectively solve this
# A good next step would be to prevent modifications of registries during test execution and
# only allow them selectively with an automatic cleanup after the test finished.
@pytest.fixture(autouse=True)
def reset_gui_registries() -> Iterator[None]:
    """Fixture to reset registries to its default entries."""
    registries: list[Registry[Any]] = [
        dashlet_registry,
        permission_registry,
        permission_section_registry,
    ]
    with reset_registries(registries):
        yield


@pytest.fixture()
def with_automation_user(request_context: None, load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="admin") as user:
        yield user


class WebTestAppForCMK(webtest.TestApp):
    """A webtest.TestApp class with helper functions for automation user APIs"""

    def __init__(self, *args, **kw) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kw)
        self.username: UserId | None = None
        self.password: str | None = None

    def set_credentials(self, username: UserId | None, password: str | None) -> None:
        self.username = username
        self.password = password

    def call_method(  # type: ignore[no-untyped-def]
        self, method: HTTPMethod, url, *args, **kw
    ) -> webtest.TestResponse:
        return getattr(self, method.lower())(url, *args, **kw)

    def has_link(self, resp: webtest.TestResponse, rel: str) -> bool:
        if resp.status_code == 204:
            return False
        try:
            _ = get_link(resp.json, expand_rel(rel))
            return True
        except KeyError:
            return False

    def follow_link(
        self,
        resp: webtest.TestResponse,
        rel: str,
        json_data: dict[str, Any] | None = None,
        **kw: object,
    ) -> webtest.TestResponse:
        """Follow a link description as defined in a restful-objects entity"""
        params = dict(kw)
        if resp.status.startswith("2") and resp.content_type.endswith("json"):
            if json_data is None:
                json_data = resp.json
            link = get_link(json_data, expand_rel(rel))
            if "body_params" in link and link["body_params"]:
                params["params"] = json.dumps(link["body_params"])
                params["content_type"] = "application/json"
            resp = self.call_method(link["method"], link["href"], **params)
        return resp

    def login(self, username: UserId, password: str) -> webtest.TestResponse:
        self.username = username
        login = self.get("/NO_SITE/check_mk/login.py", status=200)
        login.form["_username"] = username
        login.form["_password"] = password
        resp = login.form.submit("_login", index=1)
        assert "Invalid credentials." not in resp.text
        return resp


def _make_webtest(debug: bool = True, testing: bool = True) -> WebTestAppForCMK:
    cookies = CookieJar()
    return WebTestAppForCMK(session_wsgi_app(debug=debug, testing=testing), cookiejar=cookies)


@pytest.fixture()
def auth_request(
    with_user: tuple[UserId, str],
) -> typing.Generator[http.Request, None, None]:
    # NOTE:
    # REMOTE_USER will be omitted by `flask_app.test_client()` if only passed via an
    # environment dict. When however a Request is passed in, the environment of the Request will
    # not be touched.
    user_id, _ = with_user
    yield http.Request({**create_environ(path="/NO_SITE/"), "REMOTE_USER": str(user_id)})


@pytest.fixture()
def admin_auth_request(
    with_admin: tuple[UserId, str],
) -> typing.Generator[http.Request, None, None]:
    # NOTE:
    # REMOTE_USER will be omitted by `flask_app.test_client()` if only passed via an
    # environment dict. When however a Request is passed in, the environment of the Request will
    # not be touched.
    user_id, _ = with_admin
    yield http.Request({**create_environ(), "REMOTE_USER": str(user_id)})


class SingleRequest(typing.Protocol):
    def __call__(self, *, in_the_past: int = 0) -> tuple[UserId, SessionInfo]: ...


@pytest.fixture(scope="function")
def single_auth_request(flask_app: Flask, auth_request: http.Request) -> SingleRequest:
    """Do a single authenticated request, thereby persisting the session to disk."""

    def caller(*, in_the_past: int = 0) -> tuple[UserId, SessionInfo]:
        with flask_app.test_client() as client:
            client.get(auth_request)
            infos = load_session_infos(session.user.ident)

            # When `in_the_past` is a positive integer, the resulting session will have happened
            # that many seconds in the past.
            session.session_info.last_activity -= in_the_past
            session.session_info.started_at -= in_the_past

            session_id = session.session_info.session_id
            user_id = auth_request.environ["REMOTE_USER"]
            userdb.session.save_session_infos(
                user_id, session_infos={session_id: session.session_info}
            )
            assert session.user.id == user_id
            return session.user.id, infos[session_id]

    return caller


@pytest.fixture()
def wsgi_app() -> WebTestAppForCMK:
    return _make_webtest(debug=False, testing=True)


@pytest.fixture()
def wsgi_app_debug_off() -> WebTestAppForCMK:
    return _make_webtest(debug=False, testing=False)


@pytest.fixture()
def logged_in_wsgi_app(
    wsgi_app: WebTestAppForCMK, with_user: tuple[UserId, str]
) -> WebTestAppForCMK:
    _ = wsgi_app.login(with_user[0], with_user[1])
    return wsgi_app


@pytest.fixture()
def logged_in_admin_wsgi_app(
    wsgi_app: WebTestAppForCMK, with_admin: tuple[UserId, str]
) -> WebTestAppForCMK:
    wsgi_app.set_authorization(None)
    _ = wsgi_app.login(with_admin[0], with_admin[1])
    return wsgi_app


@pytest.fixture()
def aut_user_auth_wsgi_app(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: tuple[UserId, str],
) -> WebTestAppForCMK:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", f"{username} {secret}"))
    return wsgi_app


@pytest.fixture()
def with_groups(monkeypatch, request_context, with_admin_login, suppress_remote_automation_calls):
    groups.add_group("windows", "host", {"alias": "windows"})
    groups.add_group("routers", "service", {"alias": "routers"})
    groups.add_group("admins", "contact", {"alias": "admins"})
    yield
    groups.delete_group("windows", "host")
    groups.delete_group("routers", "service")
    monkeypatch.setattr(mkeventd, "get_rule_stats_from_ec", lambda: {})
    groups.delete_group("admins", "contact")


@pytest.fixture()
def with_host(
    request_context,
    with_admin_login,
):
    hostnames = [HostName("heute"), HostName("example.com")]
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts(
        [(hostname, {}, None) for hostname in hostnames],
    )
    yield hostnames
    root_folder.delete_hosts(hostnames, automation=lambda *args, **kwargs: DeleteHostsResult())


@pytest.fixture(autouse=True)
def mock__add_extensions_for_license_usage(monkeypatch):
    monkeypatch.setattr(activate_changes, "_add_extensions_for_license_usage", lambda: None)


@pytest.fixture
def run_as_user() -> Callable[[UserId], ContextManager[None]]:
    """Fixture to run parts of test-code as another user

    Examples:

        def test_function(run_as_user) -> None:
            print("Run as Nobody")
            with run_as_user(UserID("egon")):
                 print("Run as 'egon'")
            print("Run again as Nobody")

    """

    @contextmanager
    def _run_as_user(user_id: UserId) -> Iterator[None]:
        config_module.load_config()
        with UserContext(user_id):
            yield None

    return _run_as_user


@pytest.fixture
def run_as_superuser() -> Callable[[], ContextManager[None]]:
    """Fixture to run parts of test-code as the superuser

    Examples:

        def test_function(run_as_superuser) -> None:
            print("Run as Nobody")
            with run_as_superuser():
                 print("Run as Superuser")
            print("Run again as Nobody")

    """

    @contextmanager
    def _run_as_superuser() -> Iterator[None]:
        config_module.load_config()
        with SuperUserContext():
            yield None

    return _run_as_superuser


@pytest.fixture()
def flask_app() -> Flask:
    return session_wsgi_app(testing=True)


@pytest.fixture(name="base")
def fixture_base() -> str:
    return "/NO_SITE/check_mk/api/1.0"


class WebTestAppRequestHandler(RequestHandler):
    def __init__(self, wsgi_app: WebTestAppForCMK):
        self.app = wsgi_app

    def set_credentials(self, username: str, password: str) -> None:
        self.app.set_authorization(("Bearer", f"{username} {password}"))

    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, str | typing.Sequence[str]] | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        if query_params is not None:
            query_string = "?" + urllib.parse.urlencode(query_params, doseq=True)
        else:
            query_string = ""
        resp = self.app.call_method(
            method,
            url + query_string,
            params=body,
            headers=dict(headers or {}),
            expect_errors=True,
        )
        return Response(status_code=resp.status_code, body=resp.body, headers=resp.headers)


@pytest.fixture()
def api_client(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> RestApiClient:
    return RestApiClient(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)


@pytest.fixture()
def clients(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> ClientRegistry:
    return get_client_registry(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)
