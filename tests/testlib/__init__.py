#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time
import sys
import abc
import tempfile
import datetime
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    Callable,
    Generator,
    MutableMapping,
    Set,
)

import urllib3  # type: ignore[import]
import freezegun  # type: ignore[import]
import pytest
from _pytest.monkeypatch import MonkeyPatch

from testlib.utils import (  # noqa: F401 # pylint: disable=unused-import
    repo_path, cmk_path, cme_path, cmc_path, current_branch_name, virtualenv_path,
    get_cmk_download_credentials, is_running_as_site_user, site_id, add_python_paths,
    is_enterprise_repo, is_managed_repo, get_standard_linux_agent_output,
)
from testlib.fixtures import web, ec  # noqa: F401 # pylint: disable=unused-import
from testlib.site import Site, SiteFactory  # noqa: F401 # pylint: disable=unused-import
from testlib.version import CMKVersion  # noqa: F401 # pylint: disable=unused-import
from testlib.web_session import CMKWebSession, APIError  # noqa: F401 # pylint: disable=unused-import
from testlib.event_console import CMKEventConsole, CMKEventConsoleStatus  # noqa: F401 # pylint: disable=unused-import

# Disable insecure requests warning message during SSL testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def skip_unwanted_test_types(item):
    test_type = item.get_closest_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)


# Some cmk.* code is calling things like cmk_version.is_raw_edition() at import time
# (e.g. cmk/base/default_config/notify.py) for edition specific variable
# defaults. In integration tests we want to use the exact version of the
# site. For unit tests we assume we are in Enterprise Edition context.
def fake_version_and_paths():
    if is_running_as_site_user():
        return

    import _pytest.monkeypatch  # type: ignore # pylint: disable=import-outside-toplevel
    monkeypatch = _pytest.monkeypatch.MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    import cmk.utils.version as cmk_version  # pylint: disable=import-outside-toplevel
    import cmk.utils.paths  # pylint: disable=import-outside-toplevel

    if is_managed_repo():
        edition_short = "cme"
    elif is_enterprise_repo():
        edition_short = "cee"
    else:
        edition_short = "cre"

    monkeypatch.setattr(cmk_version, "omd_version", lambda: "%s.%s" %
                        (cmk_version.__version__, edition_short))

    monkeypatch.setattr("cmk.utils.paths.agents_dir", "%s/agents" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.checks_dir", "%s/checks" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.notifications_dir", Path(cmk_path()) / "notifications")
    monkeypatch.setattr("cmk.utils.paths.inventory_dir", "%s/inventory" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.inventory_output_dir",
                        os.path.join(tmp_dir, "var/check_mk/inventory"))
    monkeypatch.setattr("cmk.utils.paths.inventory_archive_dir",
                        os.path.join(tmp_dir, "var/check_mk/inventory_archive"))
    monkeypatch.setattr("cmk.utils.paths.check_manpages_dir", "%s/checkman" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.web_dir", "%s/web" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.omd_root", tmp_dir)
    monkeypatch.setattr("cmk.utils.paths.tmp_dir", os.path.join(tmp_dir, "tmp/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.counters_dir",
                        os.path.join(tmp_dir, "tmp/check_mk/counters"))
    monkeypatch.setattr("cmk.utils.paths.tcp_cache_dir", os.path.join(tmp_dir,
                                                                      "tmp/check_mk/cache"))
    monkeypatch.setattr("cmk.utils.paths.data_source_cache_dir",
                        os.path.join(tmp_dir, "tmp/check_mk/data_source_cache"))
    monkeypatch.setattr("cmk.utils.paths.var_dir", os.path.join(tmp_dir, "var/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.log_dir", os.path.join(tmp_dir, "var/log"))
    monkeypatch.setattr("cmk.utils.paths.core_helper_config_dir",
                        Path(tmp_dir, "var/check_mk/core/helper_config"))
    monkeypatch.setattr("cmk.utils.paths.autochecks_dir",
                        os.path.join(tmp_dir, "var/check_mk/autochecks"))
    monkeypatch.setattr("cmk.utils.paths.precompiled_checks_dir",
                        os.path.join(tmp_dir, "var/check_mk/precompiled_checks"))
    monkeypatch.setattr("cmk.utils.paths.crash_dir", Path(cmk.utils.paths.var_dir) / "crashes")
    monkeypatch.setattr("cmk.utils.paths.include_cache_dir",
                        os.path.join(tmp_dir, "tmp/check_mk/check_includes"))
    monkeypatch.setattr("cmk.utils.paths.check_mk_config_dir",
                        os.path.join(tmp_dir, "etc/check_mk/conf.d"))
    monkeypatch.setattr("cmk.utils.paths.main_config_file",
                        os.path.join(tmp_dir, "etc/check_mk/main.mk"))
    monkeypatch.setattr("cmk.utils.paths.default_config_dir", os.path.join(tmp_dir, "etc/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.piggyback_dir", Path(tmp_dir) / "var/check_mk/piggyback")
    monkeypatch.setattr("cmk.utils.paths.piggyback_source_dir",
                        Path(tmp_dir) / "var/check_mk/piggyback_sources")
    monkeypatch.setattr("cmk.utils.paths.htpasswd_file", os.path.join(tmp_dir, "etc/htpasswd"))

    monkeypatch.setattr("cmk.utils.paths.local_share_dir", Path(tmp_dir, "local/share/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.local_checks_dir",
                        Path(tmp_dir, "local/share/check_mk/checks"))
    monkeypatch.setattr("cmk.utils.paths.local_notifications_dir",
                        Path(tmp_dir, "local/share/check_mk/notifications"))
    monkeypatch.setattr("cmk.utils.paths.local_inventory_dir",
                        Path(tmp_dir, "local/share/check_mk/inventory"))
    monkeypatch.setattr("cmk.utils.paths.local_check_manpages_dir",
                        Path(tmp_dir, "local/share/check_mk/checkman"))
    monkeypatch.setattr("cmk.utils.paths.local_agents_dir",
                        Path(tmp_dir, "local/share/check_mk/agents"))
    monkeypatch.setattr("cmk.utils.paths.local_web_dir", Path(tmp_dir, "local/share/check_mk/web"))
    monkeypatch.setattr("cmk.utils.paths.local_pnp_templates_dir",
                        Path(tmp_dir, "local/share/check_mk/pnp-templates"))
    monkeypatch.setattr("cmk.utils.paths.local_doc_dir", Path(tmp_dir, "local/share/doc/check_mk"))
    monkeypatch.setattr("cmk.utils.paths.local_locale_dir",
                        Path(tmp_dir, "local/share/check_mk/locale"))
    monkeypatch.setattr("cmk.utils.paths.local_bin_dir", Path(tmp_dir, "local/bin"))
    monkeypatch.setattr("cmk.utils.paths.local_lib_dir", Path(tmp_dir, "local/lib"))
    monkeypatch.setattr("cmk.utils.paths.local_mib_dir", Path(tmp_dir, "local/share/snmp/mibs"))
    monkeypatch.setattr("cmk.utils.paths.diagnostics_dir",
                        Path(tmp_dir).joinpath("var/check_mk/diagnostics"))
    monkeypatch.setattr("cmk.utils.paths.site_config_dir",
                        Path(cmk.utils.paths.var_dir, "site_configs"))
    monkeypatch.setattr("cmk.utils.paths.disabled_packages_dir",
                        Path(cmk.utils.paths.var_dir, "disabled_packages"))
    monkeypatch.setattr("cmk.utils.paths.nagios_objects_file",
                        os.path.join(tmp_dir, "etc/nagios/conf.d/check_mk_objects.cfg"))
    monkeypatch.setattr("cmk.utils.paths.precompiled_hostchecks_dir",
                        os.path.join(tmp_dir, "var/check_mk/precompiled"))
    monkeypatch.setattr("cmk.utils.paths.discovered_host_labels_dir",
                        Path(tmp_dir, "var/check_mk/discovered_host_labels"))


def import_module(pathname):
    """Return the module loaded from `pathname`.

    `pathname` is a path relative to the top-level directory
    of the repository.

    This function loads the module at `pathname` even if it does not have
    the ".py" extension.

    See Also:
        - `https://mail.python.org/pipermail/python-ideas/2014-December/030265.html`.

    """
    modname = os.path.splitext(os.path.basename(pathname))[0]
    modpath = os.path.join(cmk_path(), pathname)

    import importlib  # pylint: disable=import-outside-toplevel
    # TODO: load_module() is deprecated, we should avoid using it.
    # Furhermore, due to some reflection Kung-Fu and typeshed oddities,
    # mypy is confused about its arguments.
    return importlib.machinery.SourceFileLoader(modname, modpath).load_module()  # type: ignore[call-arg] # pylint: disable=no-value-for-parameter,deprecated-method


def wait_until(condition, timeout=1, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise Exception("Timeout out waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))


class WatchLog:
    """Small helper for integration tests: Watch a sites log file"""
    def __init__(self, site, log_path, default_timeout=5):
        self._site = site
        self._log_path = log_path
        self._log = None
        self._default_timeout = default_timeout

    def __enter__(self):
        if not self._site.file_exists(self._log_path):
            self._site.write_file(self._log_path, "")

        self._log = open(self._site.path(self._log_path), "r")
        self._log.seek(0, 2)  # go to end of file
        return self

    def __exit__(self, *exc_info):
        try:
            if self._log is not None:
                self._log.close()
        except AttributeError:
            pass

    def check_logged(self, match_for, timeout=None):
        if timeout is None:
            timeout = self._default_timeout
        if not self._check_for_line(match_for, timeout):
            raise Exception("Did not find %r in %s after %d seconds" %
                            (match_for, self._log_path, timeout))

    def check_not_logged(self, match_for, timeout=None):
        if timeout is None:
            timeout = self._default_timeout
        if self._check_for_line(match_for, timeout):
            raise Exception("Found %r in %s after %d seconds" %
                            (match_for, self._log_path, timeout))

    def _check_for_line(self, match_for, timeout):
        if self._log is None:
            raise Exception("no log file")
        timeout_at = time.time() + timeout
        sys.stdout.write("Start checking for matching line at %d until %d\n" %
                         (time.time(), timeout_at))
        while time.time() < timeout_at:
            #print("read till timeout %0.2f sec left" % (timeout_at - time.time()))
            line = self._log.readline()
            if line:
                sys.stdout.write("PROCESS LINE: %r\n" % line)
            if match_for in line:
                return True
            time.sleep(0.1)

        sys.stdout.write("Timed out at %d\n" % (time.time()))
        return False


def create_linux_test_host(request, web_fixture, site, hostname):
    def finalizer():
        web_fixture.delete_host(hostname)
        web_fixture.activate_changes()

        for path in [
                "var/check_mk/agent_output/%s" % hostname,
                "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
                "tmp/check_mk/status_data/%s" % hostname,
                "tmp/check_mk/status_data/%s.gz" % hostname,
                "var/check_mk/inventory/%s" % hostname,
                "var/check_mk/inventory/%s.gz" % hostname,
        ]:
            if os.path.exists(path):
                site.delete_file(path)

    request.addfinalizer(finalizer)

    web_fixture.add_host(hostname, attributes={"ipaddress": "127.0.0.1"})

    site.write_file(
        "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['%s']))\n" %
        hostname)

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/%s" % hostname, get_standard_linux_agent_output())


#.
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Testing of Checkmk checks                                           |
#   '----------------------------------------------------------------------'


class CheckManager:
    _CHECK_FILES_LOADED: Set[str] = set()

    def load(self, file_names=None):
        """Load either all check plugins or the given file_names"""
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        import cmk.base.check_api as check_api  # pylint: disable=import-outside-toplevel
        import cmk.utils.paths  # pylint: disable=import-outside-toplevel

        if config.all_checks_loaded():
            return self  # No need to load more

        if file_names is None:
            raise RuntimeError("Loading all checks is not supported. Use the fixture "
                               "\"config_load_all_checks\" instead")

        if not set(file_names) - CheckManager._CHECK_FILES_LOADED:
            return self  # Everything needed is already loaded

        # On first call, initialize the basic data structures
        if not CheckManager._CHECK_FILES_LOADED:
            config._initialize_data_structures()

        CheckManager._CHECK_FILES_LOADED.update(set(file_names))

        config.load_checks(check_api.get_check_api_context,
                           [os.path.join(cmk.utils.paths.checks_dir, f) for f in file_names])

        return self

    def get_check(self, name):
        main_check = name.split(".", 1)[0]
        self.load([main_check])
        return Check(name)

    def get_active_check(self, name):
        self.load([name])
        return ActiveCheck(name)

    def get_special_agent(self, name):
        self.load([name])
        return SpecialAgent(name)


class MissingCheckInfoError(KeyError):
    pass


class BaseCheck(metaclass=abc.ABCMeta):
    """Abstract base class for Check and ActiveCheck"""
    def __init__(self, name):
        import cmk.base.check_api_utils  # pylint: disable=import-outside-toplevel
        self.set_hostname = cmk.base.check_api_utils.set_hostname
        self.set_service = cmk.base.check_api_utils.set_service
        self.name = name
        self.info = {}

    def set_check_api_utils_globals(self, item=None, set_service=False):
        description = None
        if set_service:
            description = self.info["service_description"]
            assert description, '%r is missing a service_description' % self.name
            if item is not None:
                assert "%s" in description, \
                    "Missing '%%s' formatter in service description of %r" \
                    % self.name
                description = description % item
        self.set_service(self.name, description)
        self.set_hostname('non-existent-testhost')


class Check(BaseCheck):
    def __init__(self, name):
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        from cmk.base.api.agent_based import register  # pylint: disable=import-outside-toplevel
        super(Check, self).__init__(name)
        if self.name not in config.check_info:
            raise MissingCheckInfoError(self.name)
        self.info = config.check_info[self.name]
        self.context = config._check_contexts[self.name]
        self._migrated_plugin = register.get_check_plugin(
            config.CheckPluginName(self.name.replace('.', '_')))

    def default_parameters(self):
        if self._migrated_plugin:
            return self._migrated_plugin.check_default_parameters or {}
        return {}

    def run_parse(self, info):
        parse_func = self.info.get("parse_function")
        if not parse_func:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no parse function defined")
        self.set_check_api_utils_globals()
        return parse_func(info)

    def run_discovery(self, info):
        disco_func = self.info.get("inventory_function")
        if not disco_func:
            raise MissingCheckInfoError("Check '%s' " % self.name +
                                        "has no discovery function defined")
        self.set_check_api_utils_globals()
        # TODO: use standard sanitizing code
        return disco_func(info)

    def run_check(self, item, params, info):
        check_func = self.info.get("check_function")
        if not check_func:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no check function defined")
        self.set_check_api_utils_globals(item, set_service=True)
        # TODO: use standard sanitizing code
        return check_func(item, params, info)

    #def run_parse_with_walk(self, walk_name):
    #    if "parse_function" not in self.info:
    #        raise Exception("This check has no parse function defined")

    #    return self.info["parse_function"]()

    #def run_discovery_with_walk(self, walk_name):
    #     # TODO: use standard walk processing code
    #    info = self._get_walk(walk_name)

    #    # TODO: use standard sanitizing code
    #    return self.info["inventory_function"](info)

    #def run_check_with_walk(self, walk_name, item, params):
    #     # TODO: use standard walk processing code
    #    info = self._get_walk(walk_name)

    #    # TODO: use standard sanitizing code
    #    return self.info["check_function"](item, params, info)


class ActiveCheck(BaseCheck):
    def __init__(self, name):
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        super(ActiveCheck, self).__init__(name)
        assert self.name.startswith(
            'check_'), 'Specify the full name of the active check, e.g. check_http'
        self.info = config.active_check_info[self.name[len('check_'):]]

    def run_argument_function(self, params):
        self.set_check_api_utils_globals()
        return self.info['argument_function'](params)

    def run_service_description(self, params):
        return self.info['service_description'](params)


class SpecialAgent:
    def __init__(self, name):
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        super(SpecialAgent, self).__init__()
        self.name = name
        assert self.name.startswith(
            'agent_'), 'Specify the full name of the active check, e.g. agent_3par'
        self.argument_func = config.special_agent_info[self.name[len('agent_'):]]


@contextmanager
def set_timezone(timezone):
    if "TZ" not in os.environ:
        tz_set = False
        old_tz = ""
    else:
        tz_set = True
        old_tz = os.environ['TZ']

    os.environ['TZ'] = timezone
    time.tzset()

    yield

    if not tz_set:
        del os.environ['TZ']
    else:
        os.environ['TZ'] = old_tz

    time.tzset()


@contextmanager
def on_time(utctime, timezone):
    """Set the time and timezone for the test"""
    if isinstance(utctime, (int, float)):
        utctime = datetime.datetime.utcfromtimestamp(utctime)

    with set_timezone(timezone), freezegun.freeze_time(utctime):
        yield


def get_value_store_fixture(
        module: ModuleType
) -> Callable[[MonkeyPatch], Generator[MutableMapping[str, Any], None, None]]:
    """Creates a fixture for patching get_value_store (check API) in a given module"""
    @pytest.fixture(name="value_store")
    def value_store_fixture(monkeypatch):
        value_store: MutableMapping[str, Any] = {}
        monkeypatch.setattr(module, 'get_value_store', lambda: value_store)
        yield value_store

    return value_store_fixture
