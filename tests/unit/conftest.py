#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import logging
import os
import shutil
from collections.abc import Callable, Generator, Iterable, Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fakeredis import FakeRedis

from tests.testlib.repo import (
    is_cloud_repo,
    is_enterprise_repo,
    is_managed_repo,
    is_saas_repo,
    repo_path,
)

# Import this fixture to not clutter this file, but it's unused here...
from tests.unit.cmk.utils.crypto.certs import (  # pylint: disable=unused-import
    fixture_ed25519_private_key,
    fixture_rsa_private_key,
    fixture_secp256k1_private_key,
    fixture_self_signed,
    fixture_self_signed_ec,
    fixture_self_signed_ed25519,
)

import livestatus

import cmk.utils.caching
import cmk.utils.crypto.password_hashing
import cmk.utils.paths
from cmk.utils import redis, tty
from cmk.utils.legacy_check_api import LegacyCheckDefinition
from cmk.utils.licensing.handler import (
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    UserEffect,
)
from cmk.utils.livestatus_helpers.testing import (
    mock_livestatus_communication,
    MockLiveStatusConnection,
)

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.site import omd_site

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def enable_debug_fixture():
    debug_mode = cmk.ccc.debug.debug_mode
    cmk.ccc.debug.enable()
    yield
    cmk.ccc.debug.debug_mode = debug_mode


@pytest.fixture
def as_path(tmp_path: Path) -> Callable[[str], Path]:
    """See Also:
    * https://docs.pytest.org/en/7.2.x/how-to/fixtures.html#factories-as-fixtures

    """

    def _as_path(walk: str) -> Path:
        data = tmp_path / "data"
        data.write_text(walk)
        return data

    return _as_path


@pytest.fixture
def disable_debug():
    debug_mode = cmk.ccc.debug.debug_mode
    cmk.ccc.debug.disable()
    yield
    cmk.ccc.debug.debug_mode = debug_mode


@pytest.fixture(autouse=True, scope="session")
def fixture_umask():
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


@pytest.fixture(name="edition", params=["cre", "cee", "cme", "cce"])
def fixture_edition(request: pytest.FixtureRequest) -> Iterable[cmk_version.Edition]:
    # The param seems to be an optional attribute which mypy can not understand
    edition_short = request.param
    if edition_short == "cse" and not is_saas_repo():
        pytest.skip("Needed files are not available")

    if edition_short == "cce" and not is_cloud_repo():
        pytest.skip("Needed files are not available")

    if edition_short == "cme" and not is_managed_repo():
        pytest.skip("Needed files are not available")

    if edition_short == "cee" and not is_enterprise_repo():
        pytest.skip("Needed files are not available")

    yield cmk_version.Edition[edition_short.upper()]


@pytest.fixture(autouse=True, scope="session")
def fixture_omd_site() -> Generator[None, None, None]:
    os.environ["OMD_SITE"] = "NO_SITE"
    yield


@pytest.fixture
def patch_omd_site(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("OMD_ROOT", str(cmk.utils.paths.omd_root))
    omd_site.cache_clear()

    _touch(cmk.utils.paths.htpasswd_file)
    store.makedirs(cmk.utils.paths.autochecks_dir)
    store.makedirs(cmk.utils.paths.var_dir + "/web")
    store.makedirs(cmk.utils.paths.var_dir + "/php-api")
    store.makedirs(cmk.utils.paths.var_dir + "/wato/php-api")
    store.makedirs(cmk.utils.paths.var_dir + "/wato/auth")
    store.makedirs(cmk.utils.paths.tmp_dir / "wato/activation")
    store.makedirs(cmk.utils.paths.omd_root / "var/log")
    store.makedirs(cmk.utils.paths.omd_root / "tmp/check_mk")
    store.makedirs(cmk.utils.paths.default_config_dir + "/conf.d/wato")
    store.makedirs(cmk.utils.paths.default_config_dir + "/multisite.d/wato")
    store.makedirs(cmk.utils.paths.default_config_dir + "/mkeventd.d/wato")
    store.makedirs(cmk.utils.paths.local_dashboards_dir)
    store.makedirs(cmk.utils.paths.local_views_dir)
    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
        # needed for visuals.load()
        store.makedirs(cmk.utils.paths.local_reports_dir)
    _touch(cmk.utils.paths.default_config_dir + "/mkeventd.mk")
    _touch(cmk.utils.paths.default_config_dir + "/multisite.mk")

    omd_config_dir = f"{cmk.utils.paths.omd_root}/etc/omd"
    _dump(
        omd_config_dir + "/site.conf",
        """CONFIG_ADMIN_MAIL=''
CONFIG_AGENT_RECEIVER='on'
CONFIG_AGENT_RECEIVER_PORT='8000'
CONFIG_APACHE_MODE='own'
CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5002'
CONFIG_AUTOSTART='off'
CONFIG_CORE='cmc'
CONFIG_LIVEPROXYD='on'
CONFIG_LIVESTATUS_TCP='off'
CONFIG_LIVESTATUS_TCP_ONLY_FROM='0.0.0.0 ::/0'
CONFIG_LIVESTATUS_TCP_PORT='6557'
CONFIG_LIVESTATUS_TCP_TLS='on'
CONFIG_MKEVENTD='on'
CONFIG_MKEVENTD_SNMPTRAP='off'
CONFIG_MKEVENTD_SYSLOG='on'
CONFIG_MKEVENTD_SYSLOG_TCP='off'
CONFIG_MULTISITE_AUTHORISATION='on'
CONFIG_MULTISITE_COOKIE_AUTH='on'
CONFIG_NSCA='off'
CONFIG_NSCA_TCP_PORT='5667'
CONFIG_PNP4NAGIOS='on'
CONFIG_TMPFS='on'""",
    )
    _dump(
        cmk.utils.paths.default_config_dir + "/mkeventd.d/wato/rules.mk",
        r"""
# Written by WATO
# encoding: utf-8

rule_packs += \
[{'id': 'default', 'title': 'Default rule pack', 'rules': [], 'disabled': False, 'hits': 0}]
""",
    )

    yield
    omd_site.cache_clear()


def _dump(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(data)


def _touch(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).touch()


@pytest.fixture(autouse=True)
def cleanup_after_test():
    yield

    if cmk.utils.paths.omd_root == Path(""):
        logger.warning("OMD_ROOT not set, skipping cleanup")
        return

    # Ensure there is no file left over in the unit test fake site
    # to prevent tests involving eachother
    for entry in cmk.utils.paths.omd_root.iterdir():
        # This randomly fails for some unclear reasons. Looks like a race condition, but I
        # currently have no idea which triggers this since the tests are not executed in
        # parallel at the moment. This is meant as quick hack, trying to reduce flaky results.
        try:
            if entry.is_dir():
                shutil.rmtree(str(entry))
            else:
                entry.unlink()
        except OSError as e:
            logger.debug("Failed to cleanup %s after test: %s. Keep going anyway", entry, e)


# Unit tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request):
    pass


def _clear_caches():
    cmk.utils.caching.cache_manager.clear()
    cmk_version.edition.cache_clear()


@pytest.fixture(autouse=True, scope="module")
def clear_caches_per_module():
    """Ensures that module-scope fixtures are executed with clean caches."""
    _clear_caches()
    yield


@pytest.fixture(autouse=True)
def clear_caches_per_function():
    """Ensures that each test is executed with a non-polluted cache from a previous test."""
    _clear_caches()
    yield


class FixRegister:
    """Access agent based plugins"""

    def __init__(self) -> None:
        # Local import to have faster pytest initialization
        from cmk.base import (  # pylint: disable=bad-option-value,import-outside-toplevel,cmk-module-layer-violation
            check_api,
            config,
        )
        from cmk.base.api.agent_based import (  # pylint: disable=bad-option-value,import-outside-toplevel,cmk-module-layer-violation
            register,
        )

        config._initialize_data_structures()
        assert not config.check_info

        errors = config.load_all_plugins(
            check_api.get_check_api_context,
            local_checks_dir=repo_path() / "no-such-path-but-thats-ok",
            checks_dir=str(repo_path() / "cmk/base/legacy_checks"),
        )
        assert not errors

        self._snmp_sections = copy.deepcopy(register._config.registered_snmp_sections)
        self._agent_sections = copy.deepcopy(register._config.registered_agent_sections)
        self._check_plugins = copy.deepcopy(register._config.registered_check_plugins)
        self._inventory_plugins = copy.deepcopy(register._config.registered_inventory_plugins)

    @property
    def snmp_sections(self):
        return self._snmp_sections

    @property
    def agent_sections(self):
        return self._agent_sections

    @property
    def check_plugins(self):
        return self._check_plugins

    @property
    def inventory_plugins(self):
        return self._inventory_plugins


class FixPluginLegacy:
    """Access legacy dicts like `check_info`"""

    def __init__(self, fixed_register: FixRegister) -> None:
        from cmk.base import (  # pylint: disable=bad-option-value,import-outside-toplevel,cmk-module-layer-violation
            config,
        )

        assert isinstance(fixed_register, FixRegister)  # make sure plug-ins are loaded

        self.check_info = {
            k: v
            for k, v in config.check_info.items()
            if isinstance(k, str) and isinstance(v, LegacyCheckDefinition)
        }
        self.active_check_info = copy.deepcopy(config.active_check_info)
        self.factory_settings = copy.deepcopy(config.factory_settings)


@pytest.fixture(scope="session", name="fix_register")
def fix_register_fixture() -> Iterator[FixRegister]:
    yield FixRegister()


@pytest.fixture(scope="session")
def fix_plugin_legacy(fix_register: FixRegister) -> Iterator[FixPluginLegacy]:
    yield FixPluginLegacy(fix_register)


@pytest.fixture(autouse=True, scope="module")
def prevent_livestatus_connect() -> Iterator[None]:
    """Prevent tests from trying to open livestatus connections. This will result in connect
    timeouts which slow down our tests."""

    orig_init = livestatus.MultiSiteConnection.__init__

    def init_mock(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        if self.deadsites:
            pytest.fail("Dead sites: %r" % self.deadsites)

    with patch.object(
        livestatus.SingleSiteConnection,
        "_create_socket",
        lambda *_: pytest.fail(
            "The test tried to use a livestatus connection. This will result in connect timeouts. "
            "Use mock_livestatus for mocking away the livestatus API"
        ),
    ) as _:
        with patch.object(livestatus.MultiSiteConnection, "__init__", init_mock) as _:
            yield


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
    with patch.object(redis, "Redis", FakeRedis) as _:
        redis.get_redis_client().flushall()
        yield


@pytest.fixture(autouse=True, scope="session")
def reduce_password_hashing_rounds() -> Iterator[None]:
    """Reduce the number of rounds for hashing with bcrypt to the allowed minimum"""
    with patch.object(cmk.utils.crypto.password_hashing, "BCRYPT_ROUNDS", 4):
        yield


@pytest.fixture(name="monkeypatch_module", scope="module")
def fixture_monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


class DummyNotificationHandler(NotificationHandler):
    def manage_notification(self) -> None:
        pass


class DummyLicensingHandler(LicensingHandler):
    @classmethod
    def make(cls) -> "DummyLicensingHandler":
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
        return DummyNotificationHandler(email_notification=None)


@pytest.fixture(name="is_licensed", scope="module")
def fixture_is_licensed(monkeypatch_module: pytest.MonkeyPatch) -> None:
    monkeypatch_module.setattr(
        "cmk.utils.licensing.registry._get_licensing_handler", DummyLicensingHandler
    )


@pytest.fixture(name="suppress_license_expiry_header")
def fixture_suppress_license_expiry_header(monkeypatch_module: pytest.MonkeyPatch) -> None:
    """Don't check if message about license expiration should be shown"""
    monkeypatch_module.setattr(
        "cmk.gui.htmllib.top_heading._may_show_license_expiry", lambda x: None
    )
