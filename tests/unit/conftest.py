#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import copy
import logging
import shutil
import socket
from pathlib import Path
from typing import Any, Iterable, Mapping, NamedTuple
from unittest import mock

import pytest
from fakeredis import FakeRedis  # type: ignore[import]

from tests.testlib import is_enterprise_repo, is_managed_repo, is_plus_repo

import livestatus

import cmk.utils.caching
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.redis as redis
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.site import omd_site

import cmk.gui.dashboard

# The openapi import below pulls a huge part of our GUI code indirectly into the process.  We need
# to have the default permissions loaded before that to fix some implicit dependencies.
# TODO: Extract the livestatus mock to some other place to reduce the dependencies here.
import cmk.gui.default_permissions
import cmk.gui.permissions
import cmk.gui.views
from cmk.gui.livestatus_utils.testing import mock_livestatus

if is_enterprise_repo():
    import cmk.cee.dcd.plugins.connectors.connectors_api.v1

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def enable_debug_fixture():
    debug_mode = cmk.utils.debug.debug_mode
    cmk.utils.debug.enable()
    yield
    cmk.utils.debug.debug_mode = debug_mode


@pytest.fixture(autouse=True)
def fixture_umask():
    """Ensure the unit tests always use the same umask"""
    with cmk.utils.misc.umask(0o0007):
        yield


@pytest.fixture(name="edition", params=["cre", "cee", "cme", "cpe"])
def fixture_edition(monkeypatch, request) -> Iterable[cmk_version.Edition]:
    edition_short = request.param
    if edition_short == "cpe" and not is_plus_repo():
        pytest.skip("Needed files are not available")

    if edition_short == "cme" and not is_managed_repo():
        pytest.skip("Needed files are not available")

    if edition_short == "cee" and not is_enterprise_repo():
        pytest.skip("Needed files are not available")

    yield cmk_version.Edition[edition_short.upper()]


@pytest.fixture(autouse=True)
def patch_omd_site(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "NO_SITE")
    omd_site.cache_clear()

    _touch(cmk.utils.paths.htpasswd_file)
    store.makedirs(cmk.utils.paths.autochecks_dir)
    store.makedirs(cmk.utils.paths.var_dir + "/web")
    store.makedirs(cmk.utils.paths.var_dir + "/php-api")
    store.makedirs(cmk.utils.paths.var_dir + "/wato/php-api")
    store.makedirs(cmk.utils.paths.var_dir + "/wato/auth")
    store.makedirs(cmk.utils.paths.tmp_dir + "/wato/activation")
    store.makedirs(cmk.utils.paths.omd_root / "var/log")
    store.makedirs(cmk.utils.paths.omd_root / "tmp/check_mk")
    store.makedirs(cmk.utils.paths.default_config_dir + "/conf.d/wato")
    store.makedirs(cmk.utils.paths.default_config_dir + "/multisite.d/wato")
    store.makedirs(cmk.utils.paths.default_config_dir + "/mkeventd.d/wato")
    _touch(cmk.utils.paths.default_config_dir + "/mkeventd.mk")
    _touch(cmk.utils.paths.default_config_dir + "/multisite.mk")

    omd_config_dir = "%s/etc/omd" % (cmk.utils.paths.omd_root,)
    _dump(
        omd_config_dir + "/site.conf",
        """
CONFIG_ADMIN_MAIL=''
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
CONFIG_NAGIOS_THEME='classicui'
CONFIG_NSCA='off'
CONFIG_NSCA_TCP_PORT='5667'
CONFIG_PNP4NAGIOS='on'
CONFIG_TMPFS='on'
    """,
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
    cmk.utils.caching.config_cache.clear()
    cmk.utils.caching.runtime_cache.clear()

    cmk_version.edition.cache_clear()


@pytest.fixture(autouse=True, scope="module")
def clear_caches_per_module():
    """Ensures that module-scope fixtures are executed with clean caches."""
    _clear_caches()


@pytest.fixture(autouse=True)
def clear_caches_per_function():
    """Ensures that each test is executed with a non-polluted cache from a previous test."""
    _clear_caches()


# TODO: This fixes our unit tests when executing the tests while the local
# resolver uses a search domain which uses wildcard resolution. e.g. in a
# network where mathias-kettner.de is in the domain search list and
# [anything].mathias-kettner.de resolves to an IP address.
# Clean this up once we don't have this situation anymore e.g. via VPN.
@pytest.fixture()
def fixup_ip_lookup(monkeypatch):
    # Fix IP lookup when
    def _getaddrinfo(host, port, family=None, socktype=None, proto=None, flags=None):
        if family == socket.AF_INET:
            # TODO: This is broken. It should return (family, type, proto, canonname, sockaddr)
            return "0.0.0.0"
        raise NotImplementedError()

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)


class FixRegister:
    """Access agent based plugins"""

    def __init__(self):
        # Local import to have faster pytest initialization
        import cmk.base.api.agent_based.register as register  # pylint: disable=bad-option-value,import-outside-toplevel
        import cmk.base.check_api as check_api  # pylint: disable=bad-option-value,import-outside-toplevel
        import cmk.base.config as config  # pylint: disable=bad-option-value,import-outside-toplevel
        import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=bad-option-value,import-outside-toplevel

        config._initialize_data_structures()
        assert config.check_info == {}

        config.load_all_agent_based_plugins(check_api.get_check_api_context)
        inventory_plugins.load_legacy_inventory_plugins(
            check_api.get_check_api_context,
            register.inventory_plugins_legacy.get_inventory_context,
        )

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

    def __init__(self, fixed_register: FixRegister):
        import cmk.base.config as config  # pylint: disable=bad-option-value,import-outside-toplevel
        import cmk.base.inventory_plugins as inventory_plugins

        assert isinstance(fixed_register, FixRegister)  # make sure plugins are loaded

        self._check_info = copy.deepcopy(config.check_info)
        self._snmp_info = copy.deepcopy(config.snmp_info)
        self._inv_info = copy.deepcopy(inventory_plugins._inv_info)
        self._active_check_info = copy.deepcopy(config.active_check_info)
        self._snmp_scan_functions = copy.deepcopy(config.snmp_scan_functions)
        self._check_variables = copy.deepcopy(config.get_check_variables())

    @property
    def check_info(self):
        return self._check_info

    @property
    def snmp_info(self):
        return self._snmp_info

    @property
    def inv_info(self):
        return self._inv_info

    @property
    def active_check_info(self):
        return self._active_check_info

    @property
    def snmp_scan_functions(self):
        return self._snmp_scan_functions

    @property
    def check_variables(self):
        return self._check_variables


@pytest.fixture(scope="session", name="fix_register")
def fix_register_fixture():
    yield FixRegister()


@pytest.fixture(scope="session")
def fix_plugin_legacy(fix_register):
    yield FixPluginLegacy(fix_register)


@pytest.fixture(autouse=True)
def prevent_livestatus_connect(monkeypatch):
    """Prevent tests from trying to open livestatus connections. This will result in connect
    timeouts which slow down our tests."""
    monkeypatch.setattr(
        livestatus.SingleSiteConnection,
        "_create_socket",
        lambda *_: pytest.fail(
            "The test tried to use a livestatus connection. This will result in connect timeouts. "
            "Use mock_livestatus for mocking away the livestatus API"
        ),
    )

    orig_init = livestatus.MultiSiteConnection.__init__

    def init_mock(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        if self.deadsites:
            pytest.fail("Dead sites: %r" % self.deadsites)

    monkeypatch.setattr(livestatus.MultiSiteConnection, "__init__", init_mock)


@pytest.fixture(name="mock_livestatus")
def _mock_livestatus():
    """Mock LiveStatus by patching MultiSiteConnection

    Use it like this:

        def test_function():
           from cmk.gui import sites
           sites.live().query("Foo")

        def test_foo(mock_livestatus):
           live = mock_livestatus
           live.expect_query("Foo")
           with live:
               # here call a function which does livestatus calls.
               test_function()


    """
    with mock_livestatus(with_context=False) as live:
        yield live


@pytest.fixture(autouse=True)
def use_fakeredis_client(monkeypatch):
    """Use fakeredis client instead of redis.Redis"""
    monkeypatch.setattr(
        redis,
        "Redis",
        FakeRedis,
    )


class _MockVSManager(NamedTuple):
    active_service_interface: Mapping[str, Any]


@pytest.fixture()
def initialised_item_state():
    mock_vs = _MockVSManager({})
    with mock.patch(
        "cmk.base.api.agent_based.value_store._global_state._active_host_value_store",
        mock_vs,
    ):
        yield


@pytest.fixture(autouse=True)
def registry_reset():
    """Fixture to reset registries to its default entries."""
    registries = [
        cmk.gui.dashboard.dashlet_registry,
        cmk.gui.views.icon_and_action_registry,
        cmk.gui.permissions.permission_registry,
        cmk.gui.permissions.permission_section_registry,
    ]
    if is_enterprise_repo():
        registries.append(
            cmk.cee.dcd.plugins.connectors.connectors_api.v1.connector_config_registry
        )
        registries.append(cmk.cee.dcd.plugins.connectors.connectors_api.v1.connector_registry)

    defaults_per_registry = [(registry, list(registry)) for registry in registries]  # type: ignore[call-overload]
    try:
        yield
    finally:
        for registry, defaults in defaults_per_registry:
            for entry in list(registry):  # type: ignore[call-overload]
                if entry not in defaults:
                    registry.unregister(entry)  # type: ignore[attr-defined]
