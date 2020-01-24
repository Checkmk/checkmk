#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=redefined-outer-name

from __future__ import print_function

import os
import glob
import pwd
import time
import re
import sys
import ast
import abc
import tempfile
import datetime
import inspect
from contextlib import contextmanager
import six

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import urllib3  # type: ignore
import freezegun  # type: ignore

from testlib.utils import (
    InterProcessLock,
    repo_path,
    cmk_path,
    cme_path,
    cmc_path,
    current_branch_name,
    virtualenv_path,
    get_cmk_download_credentials,
    is_running_as_site_user,
    site_id,
    add_python_paths,
    is_enterprise_repo,
    is_managed_repo,
)
from testlib.fixtures import web, ec
from testlib.site import Site, SiteFactory
from testlib.version import CMKVersion
from testlib.web_session import CMKWebSession, APIError
from testlib.event_console import CMKEventConsole, CMKEventConsoleStatus

# Disable insecure requests warning message during SSL testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def skip_unwanted_test_types(item):
    import pytest  # type: ignore[import] # pylint: disable=import-outside-toplevel
    test_type = item.get_closest_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)


# Some cmk.* code is calling things like cmk. is_raw_edition() at import time
# (e.g. cmk/base/default_config/notify.py) for edition specific variable
# defaults. In integration tests we want to use the exact version of the
# site. For unit tests we assume we are in Enterprise Edition context.
def fake_version_and_paths():
    if is_running_as_site_user():
        return

    import _pytest.monkeypatch  # type: ignore # pylint: disable=import-outside-toplevel
    monkeypatch = _pytest.monkeypatch.MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    import cmk  # pylint: disable=import-outside-toplevel

    # TODO: handle CME case
    #if is_managed_repo():
    #    monkeypatch.setattr(cmk, "omd_version", lambda: "%s.cee" % cmk.__version__)
    #elif is_enterprise_repo():
    if is_enterprise_repo():
        monkeypatch.setattr(cmk, "omd_version", lambda: "%s.cee" % cmk.__version__)
    else:
        monkeypatch.setattr(cmk, "omd_version", lambda: "%s.cre" % cmk.__version__)

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

    if sys.version_info[0] >= 3:
        import importlib  # pylint: disable=import-outside-toplevel
        return importlib.machinery.SourceFileLoader(modname, modpath).load_module()  # pylint: disable=no-value-for-parameter,deprecated-method

    import imp  # pylint: disable=import-outside-toplevel
    try:
        return imp.load_source(modname, modpath)
    finally:
        try:
            os.remove(modpath + "c")
        except OSError:
            pass


def wait_until(condition, timeout=1, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise Exception("Timeout out waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))


class WatchLog(object):  # pylint: disable=useless-object-inheritance
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


def create_linux_test_host(request, web, site, hostname):
    def finalizer():
        web.delete_host(hostname)
        web.activate_changes()
        site.delete_file("var/check_mk/agent_output/%s" % hostname)
        site.delete_file("etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname)

    request.addfinalizer(finalizer)

    web.add_host(hostname, attributes={"ipaddress": "127.0.0.1"})

    site.write_file(
        "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['%s']))\n" %
        hostname)

    site.makedirs("var/check_mk/agent_output/")
    site.write_file(
        "var/check_mk/agent_output/%s" % hostname,
        open("%s/tests/integration/cmk/base/test-files/linux-agent-output" % repo_path()).read())


#.
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Testing of Check_MK checks                                           |
#   '----------------------------------------------------------------------'


class CheckManager(object):  # pylint: disable=useless-object-inheritance
    def load(self, file_names=None):
        """Load either all check plugins or the given file_names"""
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
            import cmk.base.config as config  # pylint: disable=import-outside-toplevel
            import cmk.base.check_api as check_api  # pylint: disable=import-outside-toplevel
            import cmk.utils.paths  # pylint: disable=import-outside-toplevel

        if file_names is None:
            config.load_all_checks(check_api.get_check_api_context)  # loads all checks
        else:
            config._initialize_data_structures()
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


class BaseCheck(six.with_metaclass(abc.ABCMeta, object)):
    """Abstract base class for Check and ActiveCheck"""
    def __init__(self, name):
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
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
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
            import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        super(Check, self).__init__(name)
        if self.name not in config.check_info:
            raise MissingCheckInfoError(self.name)
        self.info = config.check_info[self.name]
        self.context = config._check_contexts[self.name]

    def default_parameters(self):
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
            import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        params = {}
        return config._update_with_default_check_parameters(self.name, params)

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
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
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


class SpecialAgent(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, name):
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
            import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        super(SpecialAgent, self).__init__()
        self.name = name
        assert self.name.startswith(
            'agent_'), 'Specify the full name of the active check, e.g. agent_3par'
        self.argument_func = config.special_agent_info[self.name[len('agent_'):]]


@contextmanager
def on_time(utctime, timezone):
    """Set the time and timezone for the test"""
    if isinstance(utctime, (int, float)):
        utctime = datetime.datetime.utcfromtimestamp(utctime)

    os.environ['TZ'] = timezone
    time.tzset()
    with freezegun.freeze_time(utctime):
        yield
    os.environ.pop('TZ')
    time.tzset()


#.
#   .--Inventory plugins---------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   |                         _             _                              |
#   |                   _ __ | |_   _  __ _(_)_ __  ___                    |
#   |                  | '_ \| | | | |/ _` | | '_ \/ __|                   |
#   |                  | |_) | | |_| | (_| | | | | \__ \                   |
#   |                  | .__/|_|\__,_|\__, |_|_| |_|___/                   |
#   |                  |_|            |___/                                |
#   '----------------------------------------------------------------------'


class MockStructuredDataTree(object):  # pylint: disable=useless-object-inheritance
    def __init__(self):
        self.data = {}

    def get_dict(self, path):
        return self.data.setdefault(path, dict())

    def get_list(self, path):
        return self.data.setdefault(path, list())


class InventoryPluginManager(object):  # pylint: disable=useless-object-inheritance
    def load(self):
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
            import cmk.base.inventory_plugins as inv_plugins  # pylint: disable=import-outside-toplevel
            import cmk.base.check_api as check_api  # pylint: disable=import-outside-toplevel
        g_inv_tree = MockStructuredDataTree()
        g_status_tree = MockStructuredDataTree()

        def get_inventory_context():
            return {
                "inv_tree_list": g_inv_tree.get_list,
                "inv_tree": g_inv_tree.get_dict,
            }

        inv_plugins.load_plugins(check_api.get_check_api_context, get_inventory_context)
        return g_inv_tree, g_status_tree

    def get_inventory_plugin(self, name):
        g_inv_tree, g_status_tree = self.load()
        return InventoryPlugin(name, g_inv_tree, g_status_tree)


class MissingInvInfoError(KeyError):
    pass


class InventoryPlugin(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, name, g_inv_tree, g_status_tree):
        if sys.version_info[0] < 3:
            # This has not been ported to Python 3 yet. Prevent mypy in Python 3 mode from following
            import cmk.base.inventory_plugins as inv_plugins  # pylint: disable=import-outside-toplevel
        super(InventoryPlugin, self).__init__()
        self.name = name
        if self.name not in inv_plugins.inv_info:
            raise MissingInvInfoError(self.name)
        self.info = inv_plugins.inv_info[self.name]
        self.g_inv_tree = g_inv_tree
        self.g_status_tree = g_status_tree

    def run_inventory(self, *args):
        # args contain info/parsed and/or params
        inv_function = self.info.get("inv_function")
        if not inv_function:
            raise MissingInvInfoError("Inventory plugin '%s' " % self.name +
                                      "has no inv function defined.")

        # As in inventory._do_inv_for_realhost
        inventory_tree = MockStructuredDataTree()
        status_data_tree = MockStructuredDataTree()
        from cmk.utils.misc import make_kwargs_for  # pylint: disable=import-outside-toplevel
        kwargs = make_kwargs_for(inv_function,
                                 inventory_tree=inventory_tree,
                                 status_data_tree=status_data_tree)
        inv_function(*args, **kwargs)
        if kwargs:
            return inventory_tree.data, status_data_tree.data
        return self.g_inv_tree.data, self.g_status_tree.data
