#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from __future__ import annotations

import typing
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from flask import Flask
from pytest_mock import MockerFixture
from werkzeug.test import create_environ

import cmk.gui.watolib.password_store
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui import http, login
from cmk.gui.config import Config
from cmk.gui.livestatus_utils.testing import mock_livestatus
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.gui.common_fixtures import (
    create_aut_user_auth_wsgi_app,
    create_flask_app,
    create_test_hosts,
    create_wsgi_app,
    inline_background_jobs_patches,
    patch_theme_context,
    perform_gui_cleanup_after_test,
    perform_load_config,
    perform_load_plugins,
    RemoteAutomation,
    set_config_context,
    suppress_remote_automation_calls_patches,
    validate_background_job_annotation,
)
from tests.testlib.gui.users import create_and_destroy_user
from tests.testlib.gui.web_test_app import (
    SetConfig,
    WebTestAppForCMK,
    WebTestAppRequestHandler,
)
from tests.testlib.rest_api_client import ClientRegistry, get_client_registry


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


@pytest.fixture()
def patch_theme() -> Iterator[None]:
    yield from patch_theme_context()


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
def load_config(request_context: None) -> Iterator[Config]:
    yield from perform_load_config()


@pytest.fixture(name="set_config")
def set_config_fixture() -> SetConfig:
    return set_config_context


@pytest.fixture(scope="session", autouse=True)
def load_plugins(test_edition: Edition) -> None:
    perform_load_plugins(test_edition)


@pytest.fixture()
def ui_context(load_plugins: None, load_config: Config) -> Iterator[None]:
    """Some helper fixture to provide a initialized UI context to tests outside of tests/unit/cmk/gui"""
    yield


@pytest.fixture()
def with_user(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="user", config=load_config) as user:
        yield user


@pytest.fixture()
def with_user_login(load_config: Config, with_user: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = UserId(with_user[0])
    with login.TransactionIdContext(
        user_id, UserPermissions(load_config.roles, permission_registry, {user_id: ["user"]}, [])
    ):
        yield user_id


@pytest.fixture()
def with_admin(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="admin", config=load_config) as user:
        yield user


@pytest.fixture()
def with_admin_login(load_config: Config, with_admin: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = with_admin[0]
    with login.TransactionIdContext(
        user_id, UserPermissions(load_config.roles, permission_registry, {user_id: ["admin"]}, [])
    ):
        yield user_id


@pytest.fixture()
def suppress_remote_automation_calls(mocker: MagicMock) -> Iterator[RemoteAutomation]:
    yield suppress_remote_automation_calls_patches(mocker)


@pytest.fixture()
def inline_background_jobs(mocker: MockerFixture) -> None:
    inline_background_jobs_patches(mocker)


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


@pytest.fixture()
def with_automation_user(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="admin", config=load_config) as user:
        yield user


@pytest.fixture()
def with_automation_user_not_admin(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="user", config=load_config) as user:
        yield user


@pytest.fixture()
def with_automation_user_guest(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=True, role="guest", config=load_config) as user:
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
def with_host(
    request_context,
    with_admin_login,
):
    yield from create_test_hosts()


@pytest.fixture()
def flask_app(
    patch_omd_site: None,
    use_fakeredis_client: None,
    load_plugins: None,
) -> Iterator[Flask]:
    yield from create_flask_app()


@pytest.fixture(name="base_without_version")
def fixture_base_without_version() -> str:
    return "/NO_SITE/check_mk/api"


@pytest.fixture(name="base")
def fixture_base(base_without_version: str) -> str:
    return f"{base_without_version}/1.0"


@pytest.fixture()
def clients(aut_user_auth_wsgi_app: WebTestAppForCMK, base_without_version: str) -> ClientRegistry:
    return get_client_registry(
        WebTestAppRequestHandler(aut_user_auth_wsgi_app), base_without_version
    )
