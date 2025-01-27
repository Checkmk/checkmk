#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import json
import threading
import typing
import urllib.parse
from base64 import b64encode
from collections.abc import Callable, Generator, Iterator, Mapping
from contextlib import contextmanager, nullcontext
from typing import Any, cast, ContextManager, Literal, NamedTuple
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient
from mypy_extensions import KwArg
from pytest_mock import MockerFixture
from werkzeug.test import create_environ, TestResponse

from tests.testlib.unit.rest_api_client import (
    ClientRegistry,
    expand_rel,
    get_client_registry,
    get_link,
    RequestHandler,
    Response,
    RestApiClient,
)

import cmk.utils.log
from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.user import UserId

from cmk.automations.results import DeleteHostsResult

import cmk.gui.config as config_module
import cmk.gui.mkeventd.wato as mkeventd
import cmk.gui.watolib.password_store
from cmk.gui import hooks, http, login, main_modules, userdb
from cmk.gui.config import active_config
from cmk.gui.livestatus_utils.testing import mock_livestatus
from cmk.gui.session import session, SuperUserContext, UserContext
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb.session import load_session_infos
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.json import patch_json
from cmk.gui.utils.script_helpers import session_wsgi_app
from cmk.gui.watolib import activate_changes, groups
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.wsgi.blueprints import checkmk, rest_api

from .users import create_and_destroy_user

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
    "patch",
    "options",
]  # fmt: off


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
def gui_cleanup_after_test(
    mocker: MockerFixture,
) -> Iterator[None]:
    # deactivate_search_index_building_at_requenst_end.
    mocker.patch("cmk.gui.watolib.search.updates_requested", return_value=False)
    yield
    # In case some tests use @request_memoize but don't use the request context, we'll emit the
    # clear event after each request.
    hooks.call("request-end")


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
def inline_background_jobs(mocker: MagicMock) -> None:
    """Prevent multiprocess.Process to spin off a new process

    This will run the code (non-concurrently, blocking) in the main execution path.
    """
    # Process.start spins of the new process. We tell it to just run the job instead.
    mocker.patch("multiprocessing.Process.start", new=lambda self: self.run())
    mocker.patch("multiprocessing.context.SpawnProcess.start", new=lambda self: self.run())
    # We stub out everything preventing smooth execution.
    mocker.patch("multiprocessing.Process.join")
    mocker.patch("multiprocessing.context.SpawnProcess.join")
    mocker.patch("multiprocessing.Process.pid", 1234)
    mocker.patch("multiprocessing.context.SpawnProcess.pid", 1234)
    mocker.patch("multiprocessing.Process.exitcode", 0)
    mocker.patch("multiprocessing.context.SpawnProcess.exitcode", 0)
    mocker.patch("sys.exit")
    mocker.patch("cmk.gui.background_job._process._detach_from_parent")
    mocker.patch("cmk.gui.background_job._process._open_stdout_and_stderr")
    mocker.patch("cmk.gui.background_job._process._register_signal_handlers")
    mocker.patch("cmk.gui.background_job.BackgroundJob._exit")
    mocker.patch("cmk.ccc.daemon.daemonize")
    mocker.patch("cmk.ccc.daemon.closefrom")


@pytest.fixture()
def allow_background_jobs() -> None:
    """Prevents the fail_on_unannotated_background_job_start fixture from raising an error"""
    return None


@pytest.fixture(autouse=True)
def fail_on_unannotated_background_job_start(
    request: pytest.FixtureRequest, mocker: MagicMock
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
def with_automation_user(load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="admin") as user:
        yield user


class WebTestAppForCMK(FlaskClient):
    """A `flask.testing::FlaskClient` object with helper functions for automation user APIs"""

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.response_wrapper = CmkTestResponse
        self.username: UserId | None = None
        self.password: str | None = None
        self._authorization_header_value: tuple[str, str] | None = None
        # legacy setup: webtest environment settings
        self.environ_base.update({"paste.testing": "True", "REMOTE_ADDR": "None"})

    def set_credentials(self, username: UserId | None, password: str | None) -> None:
        self.username = username
        self.password = password

    def get(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("get", *args, **kw)

    def post(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("post", *args, **kw)

    def put(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("put", *args, **kw)

    def delete(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("delete", *args, **kw)

    def patch(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("patch", *args, **kw)

    def options(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("options", *args, **kw)

    def call_method(
        self,
        method: HTTPMethod,
        url: str,
        params: bytes | str | dict | None = None,
        headers: dict | None = None,
        status: int | None = None,
        query_string: dict | None = None,
        expect_errors: bool = False,
        extra_environ: dict | None = None,
        follow_redirects: bool = False,
        **kw: Any,
    ) -> CmkTestResponse:
        """Call a method using the Flask (test) client.

        Preferrably pass arguments as keyword arguments. Mutually exclusive argument pairs include
        + 'params' / 'data'
        + 'query_string' / 'json_data'

        Refer to `werkzeug.test.EnvironBuilder` documentation for other keyword arguments.
        """

        @contextmanager
        def _update_environ_base(extra_env: dict) -> Generator[None]:
            backup = dict(self.environ_base)
            self.environ_base.update(extra_env)
            try:
                yield
            finally:
                self.environ_base.clear()
                self.environ_base.update(backup)

        if method.lower() == "get":
            _reset_cache_for_folders_and_hosts_setup()

        if params and kw.get("data", None):
            raise ValueError(
                "Pass either `params` or `data` as an input argument to `call_method`!"
            )
        if query_string and kw.get("json_data", None):
            raise ValueError(
                "Pass either `query_string` or `json_data` as an input argument to `call_method`!"
            )

        kw["data"] = kw.pop("data", params)
        kw["query_string"] = kw.pop("json_data", query_string)

        with _update_environ_base(extra_environ) if extra_environ else nullcontext():
            resp = getattr(super(), method.lower())(
                url, headers=headers, follow_redirects=follow_redirects, **kw
            )

        if status:
            assert resp.status_code == status, (
                f"Expected response code: {status}!\nResponse:\n{resp.text}"
            )

        if not expect_errors:
            assert (errors := resp.request.environ.get("wsgi.errors", [])), (
                "Found `wsgi.errors` arising from the request!\n"
                f"Status code:\n{resp.status_code}\n"
                f"Response:\n{str(resp)}\n"
                f"Errors:\n {'\n'.join(errors)}"
            )
        return resp

    def follow_link(
        self,
        resp: CmkTestResponse,
        rel: str,
        json_data: dict | None = None,
        **kw: Any,
    ) -> CmkTestResponse:
        """Follow a link description as defined in a restful-objects entity"""
        if resp.status.startswith("2") and resp.content_type.endswith("json"):
            _json_data = json_data if json_data else resp.json
            if isinstance(_json_data, dict):
                link = get_link(_json_data, expand_rel(rel))
            else:
                raise TypeError(
                    f"Expected `_json_data` to be {type(_json_data)}; found `{type(_json_data)}`!"
                )
            if "body_params" in link and link["body_params"]:
                kw["params"] = json.dumps(link["body_params"])
                kw["content_type"] = "application/json"
            resp = self.call_method(method=link["method"], url=link["href"], **kw)
        return resp

    def login(self, username: UserId, password: str) -> CmkTestResponse:
        self.username = username
        _path = "/NO_SITE/check_mk/login.py"
        data = {
            "_login": 1,
            "_username": username,
            "_password": password,
        }
        return self.post(_path, params=data, status=302)

    def set_authorization(self, value: tuple | None) -> None:
        """Enable HTTP authentication through the flask client.

        Initializes the value of environment variable `HTTP_AUTHORIZATION`.
        Reference code: `webtest.app::TestApp.set_authoriaztion`
        """

        def _to_bytes(value, charset="latin1"):
            if isinstance(value, str):
                return value.encode(charset)
            return value

        if value is None:
            del self.environ_base["HTTP_AUTHORIZATION"]
            self._authorization_header_value = None
            return
        self._authorization_header_value = value

        authtype: str
        creds: str

        if isinstance(value, tuple) and len(value) == 2:
            authtype, creds = value
            if authtype == "Basic" and creds and isinstance(creds, tuple):
                creds = ":".join(list(creds))
                creds = b64encode(_to_bytes(creds)).strip()
                creds = creds.decode("latin1")
            elif authtype in ("Bearer", "JWT") and creds and isinstance(creds, str):
                creds = creds.strip()

        try:
            self.environ_base["HTTP_AUTHORIZATION"] = f"{authtype} {creds}"
        except NameError:
            raise ValueError(
                "`Authorization` setup for test (flask) client is unsuccessful!\n"
                "Please check the `input argument` passed into the method.\n"
                "`set_authorization` accepts the following as input arguments:\n"
                "> ('Basic', ('username', 'password'))\n"
                "> ('Bearer', 'token')\n"
                "> ('JWT', 'token')\n"
            )

    def get_authorization(self) -> tuple[str, str] | None:
        return self._authorization_header_value


class CmkTestResponse(TestResponse):
    """Wrap `werkzeug.tests.TestReponse` to accomodate unit test validations."""

    def __str__(self) -> str:
        return self.text

    @property
    def json(self) -> dict:
        return cast(dict, super().json)

    @property
    def json_body(self) -> Any:
        """Alias for `TestResponse.json`"""
        return self.json

    @property
    def body(self) -> Any:
        """Alias for `TestResponse.data`."""
        return self.data


def _reset_cache_for_folders_and_hosts_setup() -> None:
    """Reset redis client and corresponding cache initialized in the Checkmk flask app context.

    Cache related to folder and hosts is reset, along with the redis client.

    NOTE: further investigation to be performed as documented in CMK-14175.
    `request_context` should be made specific to the Rest API calls.
    """
    from flask.globals import g

    if hasattr(g, "folder_tree"):
        g.folder_tree.invalidate_caches()

    if hasattr(g, "wato_redis_client"):
        del g.wato_redis_client


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


class SingleRequest(typing.Protocol):
    def __call__(self, *, in_the_past: int = 0) -> tuple[UserId, SessionInfo]: ...


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
def wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    """Yield a Flask test client."""
    flask_app.test_client_class = WebTestAppForCMK
    with flask_app.test_client() as client:
        if isinstance(client, WebTestAppForCMK):
            yield client
        else:
            raise TypeError(
                f"Expected flask client of type: 'WebTestAppForCMK' and not '{type(client)}'!"
            )


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
def flask_app(
    patch_omd_site: None,
    use_fakeredis_client: None,
    load_plugins: None,
) -> Iterator[Flask]:
    """Initialize a Flask app for testing purposes.

    Register a global htmllib.html() instance, just like in the regular GUI.
    """
    app = session_wsgi_app(debug=False, testing=True)
    with app.test_request_context():
        app.preprocess_request()
        yield app
        app.process_response(http.Response())


@pytest.fixture(name="base")
def fixture_base() -> str:
    return "/NO_SITE/check_mk/api/1.0"


class WebTestAppRequestHandler(RequestHandler):
    def __init__(self, wsgi_app: WebTestAppForCMK):
        self.client = wsgi_app

    def set_credentials(self, username: str, password: str) -> None:
        self.client.set_authorization(("Bearer", f"{username} {password}"))

    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, str | typing.Sequence[str]] | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
        follow_redirects: bool = False,
    ) -> Response:
        """Perform a request to the server.

        Note for REST API:
            * the urlencode with doseq=True converts a list to multiple query parameters
            (e.g. `?a=1&a=2`) instead of a single parameter `?a=1,2`. However, the latter also
            works with the url validation.
        """

        if query_params is not None:
            query_string = "?" + urllib.parse.urlencode(query_params, doseq=True)
        else:
            query_string = ""
        resp = self.client.call_method(
            method,
            url + query_string,
            params=body,
            headers=dict(headers or {}),
            expect_errors=True,
            follow_redirects=follow_redirects,
        )
        return Response(status_code=resp.status_code, body=resp.body, headers=dict(resp.headers))


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
