#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import typing
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from flask import Flask
from pytest_mock import MockerFixture
from werkzeug.test import create_environ

from tests.testlib.unit.rest_api_client import (
    ClientRegistry,
    get_client_registry,
)

from tests.unit.cmk.gui.users import create_and_destroy_user
from tests.unit.cmk.web_test_app import WebTestAppForCMK, WebTestAppRequestHandler

import cmk.utils.log
from cmk.utils.user import UserId

import cmk.gui.config as config_module
import cmk.gui.watolib.password_store
from cmk.gui import hooks, http, login, main_modules
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import session_wsgi_app


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
def aut_user_auth_wsgi_app(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: tuple[UserId, str],
) -> WebTestAppForCMK:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", f"{username} {secret}"))
    return wsgi_app


@pytest.fixture()
def clients(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> ClientRegistry:
    return get_client_registry(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)


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


@pytest.fixture(name="base")
def fixture_base() -> str:
    return "/NO_SITE/check_mk/api/1.0"


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
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of `flask_app` fixture."""
    yield


@pytest.fixture()
def with_automation_user(load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="admin") as user:
        yield user


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
def with_user(load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="user") as user:
        yield user


@pytest.fixture()
def with_user_login(with_user: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = UserId(with_user[0])
    with login.TransactionIdContext(user_id):
        yield user_id


@pytest.fixture()
def ui_context(load_plugins: None, load_config: None) -> Iterator[None]:
    """Some helper fixture to provide a initialized UI context to tests outside of tests/unit/cmk/gui"""
    yield


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
