#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

# pylint: disable=redefined-outer-name
from __future__ import annotations

import json
import threading
import typing
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, ContextManager, NamedTuple
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from pytest_mock import MockerFixture
from werkzeug.test import create_environ

from tests.testlib.unit.rest_api_client import (
    RestApiClient,
)

from tests.unit.cmk.web_test_app import (
    SetConfig,
    SingleRequest,
    WebTestAppForCMK,
    WebTestAppRequestHandler,
)

import cmk.utils.log
from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.user import UserId

from cmk.automations.results import DeleteHostsResult

import cmk.gui.config as config_module
import cmk.gui.mkeventd.wato as mkeventd
import cmk.gui.watolib.password_store
from cmk.gui import http, userdb
from cmk.gui.config import active_config
from cmk.gui.livestatus_utils.testing import mock_livestatus
from cmk.gui.session import session, SuperUserContext, UserContext
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb.session import load_session_infos
from cmk.gui.utils.json import patch_json
from cmk.gui.utils.script_helpers import session_wsgi_app
from cmk.gui.watolib import activate_changes, groups
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.wsgi.blueprints import checkmk, rest_api

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
            "cmk.gui.utils.theme.Theme.detect_icon_path",
            new=fake_detect_icon_path,
        ),
        patch(
            "cmk.gui.utils.theme.Theme.get",
            return_value="modern-dark",
        ),
        patch(
            "cmk.gui.utils.theme.theme_choices",
            return_value=[("modern-dark", "dark ut"), ("facelift", "light ut")],
        ),
    ):
        yield


@pytest.fixture(name="mock_livestatus")
def fixture_mock_livestatus() -> Iterator[MockLiveStatusConnection]:
    """UI specific override of the global mock_livestatus fixture"""
    with mock_livestatus() as mock_live:
        yield mock_live


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


@pytest.fixture(name="patch_json", autouse=True)
def fixture_patch_json() -> Iterator[None]:
    with patch_json(json):
        yield


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
    """Unannotated background job call

    Tests must not execute logic in background job processes, which may continue to run
    independently of the test case.

    If your test shall execute a background job, the default is to annotate your test with the
    `inline_background_jobs` fixture above. It makes the background job run synchronously so that
    the test code waits for the job to complete. In many cases this is the desired behavior and
    makes it easier to deal with the jobs in the tests.

    However, in some cases you actually want to have a backrgound job being executed as in the
    production environment. In that case, you need to define a local  klacono-op finamed
    "inline_background_jobs" to override these global fixtures.xture

    This autoload fixture is here to make you aware of the fact that you are calling a background
    job and that you have to decide explicitly which behavior you want to have.
    """
    if (
        "inline_background_jobs" in request.fixturenames
        or "allow_background_jobs" in request.fixturenames
    ):
        return

    mocker.patch(
        "cmk.gui.background_job._base.BackgroundJob.start",
        side_effect=RuntimeError(fail_on_unannotated_background_job_start.__doc__),
    )


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
def auth_request(with_user: tuple[UserId, str]) -> typing.Generator[http.Request]:
    # NOTE:
    # REMOTE_USER will be omitted by `flask_app.test_client()` if only passed via an
    # environment dict. When however a Request is passed in, the environment of the Request will
    # not be touched.
    user_id, _ = with_user
    yield http.Request({**create_environ(path="/NO_SITE/"), "REMOTE_USER": str(user_id)})


@pytest.fixture(scope="function")
def single_auth_request(wsgi_app: WebTestAppForCMK, auth_request: http.Request) -> SingleRequest:
    """Do a single authenticated request, thereby persisting the session to disk."""

    def caller(*, in_the_past: int = 0) -> tuple[UserId, SessionInfo]:
        wsgi_app.get(auth_request)
        infos = load_session_infos(session.user.ident)

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
def with_groups(monkeypatch, request_context, with_admin_login, suppress_remote_automation_calls):
    groups.add_group("windows", "host", {"alias": "windows"})
    groups.add_group("routers", "service", {"alias": "routers"})
    groups.add_group("admins", "contact", {"alias": "admins"})
    yield
    groups.delete_group("windows", "host")
    groups.delete_group("routers", "service")
    monkeypatch.setattr(mkeventd, "_get_rule_stats_from_ec", lambda: {})
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


@pytest.fixture
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
def api_client(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> RestApiClient:
    return RestApiClient(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)


@pytest.fixture(name="fresh_app_instance", scope="function")
def clear_caches_flask_app():
    session_wsgi_app.cache_clear()
    rest_api.app_instance.cache_clear()
    checkmk.app_instance.cache_clear()
