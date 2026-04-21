#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import logging
import os
import queue
from collections.abc import Generator, Iterator

import pytest

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
from cmk.ccc import tty
from cmk.checkengine.plugins import (  # astrein: disable=cmk-module-layer-violation
    AgentBasedPlugins,
)
from cmk.livestatus_client.testing import (
    mock_livestatus_communication,
    MockLiveStatusConnection,
)
from tests.unit.mocks_and_helpers import DummyLicensingHandler

# TODO: Can we somehow push some of the registrations below to the subdirectories?
# Needs to be executed before the import of those modules
pytest.register_assert_rewrite(
    "tests.testlib",
    "tests.unit.cmk.legacy_checks.checktestlib",
)


from tests.testlib import fake_site  # noqa: E402
from tests.testlib.common.repo import add_python_paths  # noqa: E402

logger = logging.getLogger(__name__)
logging.getLogger("faker").setLevel(logging.ERROR)

# This allows exceptions to be handled by IDEs (rather than just printing the results)
# when pytest based tests are being run from inside the IDE
# To enable this, set `_PYTEST_RAISE` to some value != '0' in your IDE
PYTEST_RAISE = os.getenv("_PYTEST_RAISE", "0") != "0"


# Cleanup temporary directory created above
@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk() -> Generator[None]:
    yield from fake_site.cleanup_cmk_tmp_dir()


# Run _fake_paths() and add_python_paths() before test execution
fake_site.fake_paths()
add_python_paths()


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


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(
    node: pytest.Item | pytest.Collector,
    call: pytest.CallInfo,
    report: pytest.CollectReport | pytest.TestReport,
) -> None:
    if not (excinfo := call.excinfo):
        return

    excp_ = excinfo.value
    report.longrepr = node.repr_failure(excinfo)
    if PYTEST_RAISE:
        raise excp_


@pytest.fixture(autouse=True)
def enable_debug_fixture() -> Generator[None]:
    yield from fake_site.enable_cmk_debug()


@pytest.fixture
def disable_debug() -> Generator[None]:
    debug_mode = cmk.ccc.debug.debug_mode
    cmk.ccc.debug.disable()
    yield
    cmk.ccc.debug.debug_mode = debug_mode


@pytest.fixture(autouse=True, scope="session")
def fixture_umask() -> Generator[None]:
    """Ensure the unit tests always use the same umask"""
    old_mask = os.umask(0o0007)
    try:
        yield
    finally:
        os.umask(old_mask)


@pytest.fixture(name="capsys")
def fixture_capsys(capsys: pytest.CaptureFixture[str]) -> Iterator[pytest.CaptureFixture[str]]:
    """Ensure that the capsys handling is deterministic even if started via `pytest -s`"""
    tty.reinit()
    try:
        yield capsys
    finally:
        tty.reinit()


@pytest.fixture(autouse=True, scope="session")
def fixture_omd_site() -> Generator[None]:
    os.environ["OMD_SITE"] = "NO_SITE"
    yield


@pytest.fixture
def patch_omd_site(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from fake_site.setup_fake_omd_site(monkeypatch)


@pytest.fixture(autouse=True)
def cleanup_after_test() -> Generator[None]:
    yield from fake_site.cleanup_omd_root_after_test()


# Unit tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request: pytest.FixtureRequest) -> None:
    pass


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


@pytest.fixture(scope="session")
def agent_based_plugins(tmp_path_factory: pytest.TempPathFactory) -> Generator[AgentBasedPlugins]:
    # Local import to have faster pytest initialization
    from cmk.base import config  # astrein: disable=cmk-module-layer-violation

    plugins = config.load_all_plugins()
    assert not plugins.errors
    yield plugins


@pytest.fixture(autouse=True, scope="module")
def prevent_livestatus_connect() -> Iterator[None]:
    """Prevent tests from trying to open livestatus connections. This will result in connect
    timeouts which slow down our tests."""
    yield from fake_site.prevent_livestatus_connect()


@pytest.fixture(name="mock_livestatus")
def fixture_mock_livestatus() -> Iterator[MockLiveStatusConnection]:
    """Mock LiveStatus by patching MultiSiteConnection

    Use it like this:

        def test_function() -> None:
           livestatus.LocalConnection().query("Foo")

        def test_foo(mock_livestatus) -> None:
           live = mock_livestatus
           live.expect_query("Foo")
           with live:
               # here call a function which does livestatus calls.
               test_function()
    """
    with mock_livestatus_communication() as mock_live:
        yield mock_live


@pytest.fixture(scope="module")
def use_fakeredis_client() -> Iterator[None]:
    """Use fakeredis client instead of redis.Redis"""
    yield from fake_site.use_fakeredis()


@pytest.fixture(autouse=True, scope="session")
def reduce_password_hashing_rounds() -> Iterator[None]:
    """Reduce the number of rounds for hashing with bcrypt to the allowed minimum"""
    yield from fake_site.reduce_password_hashing_rounds()


@pytest.fixture(autouse=True, scope="session")
def prevent_security_event_file_logging() -> Iterator[queue.Queue[logging.LogRecord]]:
    """cmk.utils.log.security_event.log_security_event implicitly opens a file logger upon it's
    first call which we want to avoid in the unit test context."""
    yield from fake_site.prevent_security_event_file_logging()


@pytest.fixture(name="monkeypatch_module", scope="module")
def fixture_monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(name="is_licensed", scope="module")
def fixture_is_licensed(monkeypatch_module: pytest.MonkeyPatch) -> None:
    monkeypatch_module.setattr(
        "cmk.licensing.registry._get_licensing_handler_factory",
        lambda omd_root: DummyLicensingHandler.make,
    )


@pytest.fixture(name="suppress_license_expiry_header")
def fixture_suppress_license_expiry_header(monkeypatch_module: pytest.MonkeyPatch) -> None:
    """Don't check if message about license expiration should be shown"""
    monkeypatch_module.setattr("cmk.gui.top_heading._may_show_license_expiry", lambda x, y: None)


@pytest.fixture(name="suppress_license_banner")
def fixture_suppress_license_banner(monkeypatch_module: pytest.MonkeyPatch) -> None:
    """Don't check if message about license expiration should be shown"""
    monkeypatch_module.setattr("cmk.gui.top_heading._may_show_license_banner", lambda x, y: None)
