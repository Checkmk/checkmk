#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"


from __future__ import annotations

import logging
import os
import queue
from collections.abc import Generator, Iterator
from unittest.mock import MagicMock

import pytest

import cmk.ccc.version as cmk_version

# NOTE: register_assert_rewrite + fake_paths must run BEFORE any cmk.gui/cmk.licensing imports.
# Modules like cmk/gui/userdb/store.py capture `cmk.utils.paths.var_dir` at import time; patching
# after those imports is too late and yields relative paths at runtime.
pytest.register_assert_rewrite("tests.testlib")


from tests.testlib import fake_site  # noqa: E402
from tests.testlib.common.repo import add_python_paths  # noqa: E402

fake_site.fake_paths()
add_python_paths()


from flask import Flask  # noqa: E402
from pytest_mock import MockerFixture  # noqa: E402

import cmk.gui.watolib.password_store  # noqa: E402
from cmk.ccc.user import UserId  # noqa: E402
from cmk.gui import login  # noqa: E402
from cmk.gui.config import Config  # noqa: E402
from cmk.gui.livestatus_utils.testing import mock_livestatus  # noqa: E402
from cmk.gui.permissions import permission_registry  # noqa: E402
from cmk.gui.utils.roles import UserPermissions  # noqa: E402
from cmk.licensing.handler import (  # noqa: E402
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    UserEffect,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection  # noqa: E402
from tests.testlib.gui.common_fixtures import (  # noqa: E402
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
from tests.testlib.gui.openapi_test_helper import (  # noqa: E402
    clear_app_instance_caches,
    create_api_client,
    create_sample_host_context,
    create_test_groups,
)
from tests.testlib.gui.users import create_and_destroy_user  # noqa: E402
from tests.testlib.gui.web_test_app import (  # noqa: E402
    SetConfig,
    WebTestAppForCMK,
    WebTestAppRequestHandler,
)
from tests.testlib.rest_api_client import (  # noqa: E402
    ClientRegistry,
    get_client_registry,
    RestApiClient,
)


class _DummyNotificationHandler(NotificationHandler):
    def manage_notification(self) -> None:
        pass


class DummyLicensingHandler(LicensingHandler):
    @classmethod
    def make(cls) -> DummyLicensingHandler:
        return cls()

    @property
    def state(self) -> LicenseState:
        return LicenseState.LICENSED

    @property
    def message(self) -> str:
        return ""

    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    @property
    def notification_handler(self) -> NotificationHandler:
        return _DummyNotificationHandler(email_notification=None)


logger = logging.getLogger(__name__)
logging.getLogger("faker").setLevel(logging.ERROR)

# This allows exceptions to be handled by IDEs (rather than just printing the results)
# when pytest based tests are being run from inside the IDE
# To enable this, set `_PYTEST_RAISE` to some value != '0' in your IDE
PYTEST_RAISE = os.getenv("_PYTEST_RAISE", "0") != "0"


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(
    node: pytest.Item | pytest.Collector,
    call: pytest.CallInfo[object],
    report: pytest.CollectReport | pytest.TestReport,
) -> None:
    if not (excinfo := call.excinfo):
        return

    excp_ = excinfo.value
    report.longrepr = node.repr_failure(excinfo)
    if PYTEST_RAISE:
        raise excp_


@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk() -> Generator[None]:
    yield from fake_site.cleanup_cmk_tmp_dir()


@pytest.fixture(autouse=True, scope="session")
def fixture_umask() -> Generator[None]:
    """Ensure the tests always use the same umask"""
    old_mask = os.umask(0o0007)
    try:
        yield
    finally:
        os.umask(old_mask)


@pytest.fixture(autouse=True, scope="session")
def fixture_omd_site() -> Generator[None]:
    os.environ["OMD_SITE"] = "NO_SITE"
    yield


@pytest.fixture(autouse=True)
def enable_debug_fixture() -> Generator[None]:
    yield from fake_site.enable_cmk_debug()


@pytest.fixture(autouse=True)
def cleanup_after_test() -> Generator[None]:
    yield from fake_site.cleanup_omd_root_after_test()


@pytest.fixture(autouse=True, scope="module")
def prevent_livestatus_connect() -> Iterator[None]:
    """Prevent tests from trying to open livestatus connections. This will result in connect
    timeouts which slow down our tests."""
    yield from fake_site.prevent_livestatus_connect()


@pytest.fixture(autouse=True, scope="module")
def clear_caches_per_module() -> Generator[None]:
    """Ensures that module-scope fixtures are executed with clean caches."""
    fake_site.clear_caches()
    yield


@pytest.fixture(autouse=True)
def clear_caches_per_function() -> Generator[None]:
    """Ensures that each test is executed with a non-polluted cache from a previous test."""
    fake_site.clear_caches()
    yield


@pytest.fixture(autouse=True, scope="session")
def reduce_password_hashing_rounds() -> Iterator[None]:
    """Reduce the number of rounds for hashing with bcrypt to the allowed minimum"""
    yield from fake_site.reduce_password_hashing_rounds()


@pytest.fixture(autouse=True, scope="session")
def prevent_security_event_file_logging() -> Iterator[queue.Queue[logging.LogRecord]]:
    """cmk.utils.log.security_event.log_security_event implicitly opens a file logger upon it's
    first call which we want to avoid in the unit test context."""
    yield from fake_site.prevent_security_event_file_logging()


@pytest.fixture(scope="session")
def test_edition() -> cmk_version.Edition:
    return fake_site.edition()


@pytest.fixture(scope="session", autouse=True)
def patch_omd_version(test_edition: cmk_version.Edition) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cmk_version, "orig_omd_version", cmk_version.omd_version, raising=False)
        mp.setattr(
            cmk_version,
            "omd_version",
            lambda *args, **kw: f"{cmk_version.__version__}.{test_edition.long}",
        )
        cmk_version.edition.cache_clear()
        yield


@pytest.fixture
def patch_omd_site(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from fake_site.setup_fake_omd_site(monkeypatch)


@pytest.fixture(scope="module")
def use_fakeredis_client() -> Iterator[None]:
    """Use fakeredis client instead of redis.Redis"""
    yield from fake_site.use_fakeredis()


@pytest.fixture(name="monkeypatch_module", scope="module")
def fixture_monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(name="is_licensed", scope="module")
def fixture_is_licensed(monkeypatch_module: pytest.MonkeyPatch) -> None:
    monkeypatch_module.setattr(
        "cmk.licensing.registry._get_licensing_handler_factory",
        lambda omd_root: DummyLicensingHandler,
    )


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
def gui_cleanup_after_test(mocker: MockerFixture) -> Iterator[None]:
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
    """UI specific mock_livestatus fixture (overrides the Layer-1 generic one)."""
    with mock_livestatus() as mock_live:
        yield mock_live


@pytest.fixture()
def load_config(request_context: None) -> Iterator[Config]:
    yield from perform_load_config()


@pytest.fixture(name="set_config")
def set_config_fixture() -> SetConfig:
    return set_config_context


@pytest.fixture(scope="session", autouse=True)
def load_plugins(test_edition: cmk_version.Edition) -> None:
    perform_load_plugins(test_edition)


@pytest.fixture()
def with_user(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="user", config=load_config) as user:
        yield user


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
def with_host(request_context, with_admin_login):
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


@pytest.fixture()
def api_client(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base_without_version: str
) -> RestApiClient:
    return create_api_client(aut_user_auth_wsgi_app, base_without_version)


@pytest.fixture()
def with_groups(
    monkeypatch: pytest.MonkeyPatch,
    request_context,
    with_admin_login,
    suppress_remote_automation_calls,
) -> Iterator[None]:
    yield from create_test_groups(monkeypatch)


@pytest.fixture(name="sample_host")
def fixture_sample_host(request_context: None) -> Iterator[str]:
    yield from create_sample_host_context()


@pytest.fixture(name="fresh_app_instance", scope="function")
def clear_caches_flask_app() -> None:
    clear_app_instance_caches()
