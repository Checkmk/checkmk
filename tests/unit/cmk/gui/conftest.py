#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import threading
import typing
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, NamedTuple
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from pytest_mock import MockerFixture
from werkzeug.test import create_environ

from tests.testlib.unit.rest_api_client import (
    ClientRegistry,
    get_client_registry,
    RestApiClient,
)

from tests.unit.cmk.gui.common_fixtures import (
    create_aut_user_auth_wsgi_app,
    create_flask_app,
    create_wsgi_app,
    perform_gui_cleanup_after_test,
    perform_load_config,
    perform_load_plugins,
    validate_background_job_annotation,
)
from tests.unit.cmk.web_test_app import (
    SetConfig,
    SingleRequest,
    WebTestAppForCMK,
    WebTestAppRequestHandler,
)

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId

import cmk.utils.log
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.automations.results import DeleteHostsResult

import cmk.gui.config as config_module
import cmk.gui.mkeventd.wato as mkeventd
import cmk.gui.watolib.password_store
from cmk.gui import http, login, userdb
from cmk.gui.config import active_config
from cmk.gui.livestatus_utils.testing import mock_livestatus
from cmk.gui.session import session
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb.session import load_session_infos
from cmk.gui.utils.script_helpers import session_wsgi_app
from cmk.gui.watolib import activate_changes, groups
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.wsgi.blueprints import checkmk, rest_api

from .users import create_and_destroy_user

SPEC_LOCK = threading.Lock()


class RemoteAutomation(NamedTuple):
    automation: MagicMock
    responses: Any


@pytest.fixture
def mock_password_file_regeneration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.password_store,
        cmk.gui.watolib.password_store.update_passwords_merged_file.__name__,
        lambda: None,
    )


@pytest.fixture(autouse=True)
def disable_automation_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("_CMK_AUTOMATIONS_FORCE_CLI_INTERFACE", "1")


@pytest.fixture(autouse=True)
def execute_background_jobs_without_job_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("_CMK_BG_JOBS_WITHOUT_JOB_SCHEDULER", "1")


@pytest.fixture(autouse=True)
def gui_cleanup_after_test(
    mocker: MockerFixture,
) -> Iterator[None]:
    yield from perform_gui_cleanup_after_test(mocker)


def fake_detect_icon_path(_: None, icon_name: str = "", prefix: str = "") -> str:
    if icon_name == "link":
        return "themes/facelift/images/icon_link.png"
    if icon_name == "info":
        return "themes/facelift/images/icon_info.svg"
    return "unittest.png"


@pytest.fixture()
def patch_theme() -> Iterator[None]:
    with (
        patch(
            "cmk.gui.htmllib.html.HTMLGenerator._inject_vue_frontend",
        ),
        patch(
            "cmk.gui.theme.Theme.detect_icon_path",
            new=fake_detect_icon_path,
        ),
        patch(
            "cmk.gui.theme.Theme.get",
            return_value="modern-dark",
        ),
        patch(
            "cmk.gui.theme.choices.theme_choices",
            return_value=[("modern-dark", "dark ut"), ("facelift", "light ut")],
        ),
    ):
        yield


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of `flask_app` fixture."""
    yield


@pytest.fixture(name="mock_livestatus")
def fixture_mock_livestatus() -> Iterator[MockLiveStatusConnection]:
    """UI specific override of the global mock_livestatus fixture"""
    with mock_livestatus() as mock_live:
        yield mock_live


@pytest.fixture()
def load_config(request_context: None) -> Iterator[None]:
    yield from perform_load_config()


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
                    "cmk.gui.single_global_setting._load_single_global_wato_setting",
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
    perform_load_plugins()


@pytest.fixture()
def ui_context(load_plugins: None, load_config: None) -> Iterator[None]:
    """Some helper fixture to provide a initialized UI context to tests outside of tests/unit/cmk/gui"""
    yield


@pytest.fixture()
def with_user(load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="user") as user:
        yield user


@pytest.fixture()
def with_user_login(with_user: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = UserId(with_user[0])
    with login.TransactionIdContext(user_id):
        yield user_id


@pytest.fixture()
def with_admin(load_config: None) -> Iterator[tuple[UserId, str]]:
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
def inline_background_jobs(mocker: MockerFixture) -> None:
    """Prevent threading.Thread to spin off a new thread

    This will run the code (non-concurrently, blocking) in the main execution path.
    """
    # Thread.start spins of the new thread. We tell it to just run the job instead.
    mocker.patch("threading.Thread.start", new=lambda self: self.run())
    ####
    mocker.patch("multiprocessing.Process.start", new=lambda self: self.run())
    mocker.patch("multiprocessing.context.SpawnProcess.start", new=lambda self: self.run())
    # We stub out everything preventing smooth execution.
    mocker.patch("threading.Thread.join")
    mocker.patch("multiprocessing.Process.join")
    mocker.patch("multiprocessing.context.SpawnProcess.join")
    mocker.patch("multiprocessing.Process.pid", 1234)
    mocker.patch("multiprocessing.context.SpawnProcess.pid", 1234)
    mocker.patch("multiprocessing.Process.exitcode", 0)
    mocker.patch("multiprocessing.context.SpawnProcess.exitcode", 0)

    class SynchronousQueue(list):
        def put(self, x: Any) -> None:
            self.append(x)

        def get(self) -> Any:
            return self.pop()

        def empty(self) -> bool:
            return not bool(self)

    mocker.patch("multiprocessing.Queue", wraps=SynchronousQueue)
    # ThreadPool creates its own Process internally so we need to mock explictly
    thread_pool_mock = mocker.patch("multiprocessing.pool.ThreadPool")
    thread_pool_mock.return_value.__enter__.return_value.apply_async = (
        lambda func, args=None, kwds=None, callback=(lambda *_args: None): callback(
            func(*(args or ()), **(kwds or {}))
        )
    )
    mocker.patch("sys.exit")
    mocker.patch("cmk.ccc.daemon.daemonize")
    mocker.patch("cmk.ccc.daemon.closefrom")


@pytest.fixture()
def allow_background_jobs() -> None:
    """Prevents the fail_on_unannotated_background_job_start fixture from raising an error"""
    return None


@pytest.fixture(autouse=True)
def fail_on_unannotated_background_job_start(
    request: pytest.FixtureRequest, mocker: MockerFixture
) -> None:
    validate_background_job_annotation(request, mocker)


@pytest.fixture(name="suppress_bake_agents_in_background")
def fixture_suppress_bake_agents_in_background(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.bakery.try_bake_agents_for_hosts",
        side_effect=lambda *args, **kw: None,
    )


@pytest.fixture(name="suppress_spec_generation_in_background")
def suppress_spec_generation_in_background(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.openapi.spec.spec_generator_job.trigger_spec_generation_in_background",
    )


@pytest.fixture()
def with_automation_user(load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="admin") as user:
        yield user


@pytest.fixture()
def auth_request(with_user: tuple[UserId, str]) -> typing.Generator[http.Request]:
    # NOTE:
    # REMOTE_USER will be omitted by `flask_app.test_client()` if only passed via an
    # environment dict. When however a Request is passed in, the environment of the Request will
    # not be touched.
    user_id, _ = with_user
    yield http.Request({**create_environ(path="/NO_SITE/"), "REMOTE_USER": str(user_id)})


@pytest.fixture()
def admin_auth_request(
    with_admin: tuple[UserId, str],
) -> typing.Generator[http.Request]:
    # NOTE:
    # REMOTE_USER will be omitted by `flask_app.test_client()` if only passed via an
    # environment dict. When however a Request is passed in, the environment of the Request will
    # not be touched.
    user_id, _ = with_admin
    yield http.Request({**create_environ(), "REMOTE_USER": str(user_id)})


@pytest.fixture(scope="function")
def single_auth_request(wsgi_app: WebTestAppForCMK, auth_request: http.Request) -> SingleRequest:
    """Do a single authenticated request, thereby persisting the session to disk."""

    def caller(*, in_the_past: int = 0) -> tuple[UserId, SessionInfo]:
        wsgi_app.get(auth_request)
        infos = load_session_infos(session.user.ident, lock=True)

        # When `in_the_past` is a positive integer, the resulting session will have happened
        # that many seconds in the past.
        session.session_info.last_activity -= in_the_past
        session.session_info.started_at -= in_the_past

        session_id = session.session_info.session_id
        user_id = auth_request.environ["REMOTE_USER"]
        userdb.session.save_session_infos(user_id, session_infos={session_id: session.session_info})
        assert session.user.id == user_id
        return session.user.id, infos[session_id]

    return caller


@pytest.fixture()
def wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    yield from create_wsgi_app(flask_app)


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
    _ = wsgi_app.login(with_admin[0], with_admin[1])
    return wsgi_app


@pytest.fixture()
def aut_user_auth_wsgi_app(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: tuple[UserId, str],
) -> WebTestAppForCMK:
    return create_aut_user_auth_wsgi_app(wsgi_app, with_automation_user)


@pytest.fixture()
def with_groups(monkeypatch, request_context, with_admin_login, suppress_remote_automation_calls):
    groups.add_group("windows", "host", {"alias": "windows"}, pprint_value=False)
    groups.add_group("routers", "service", {"alias": "routers"}, pprint_value=False)
    groups.add_group("admins", "contact", {"alias": "admins"}, pprint_value=False)
    yield
    groups.delete_group("windows", "host", pprint_value=False)
    groups.delete_group("routers", "service", pprint_value=False)
    monkeypatch.setattr(mkeventd, "_get_rule_stats_from_ec", lambda: {})
    groups.delete_group("admins", "contact", pprint_value=False)


@pytest.fixture()
def with_host(
    request_context,
    with_admin_login,
):
    hostnames = [HostName("heute"), HostName("example.com")]
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts([(hostname, {}, None) for hostname in hostnames], pprint_value=False)
    yield hostnames
    root_folder.delete_hosts(
        hostnames,
        automation=lambda *args, **kwargs: DeleteHostsResult(),
        pprint_value=False,
        debug=False,
    )


@pytest.fixture
def mock__add_extensions_for_license_usage(monkeypatch):
    monkeypatch.setattr(activate_changes, "_add_extensions_for_license_usage", lambda: None)


@pytest.fixture()
def flask_app(
    patch_omd_site: None,
    use_fakeredis_client: None,
    load_plugins: None,
) -> Iterator[Flask]:
    yield from create_flask_app()


@pytest.fixture(name="base")
def fixture_base() -> str:
    return "/NO_SITE/check_mk/api/1.0"


@pytest.fixture()
def api_client(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> RestApiClient:
    return RestApiClient(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)


@pytest.fixture()
def clients(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> ClientRegistry:
    return get_client_registry(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)


@pytest.fixture(name="fresh_app_instance", scope="function")
def clear_caches_flask_app():
    session_wsgi_app.cache_clear()
    rest_api.app_instance.cache_clear()
    checkmk.app_instance.cache_clear()
