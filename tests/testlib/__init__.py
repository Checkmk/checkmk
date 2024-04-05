#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import datetime
import fcntl
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Collection, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Final

import freezegun
import pytest
import urllib3
from psutil import Process

from tests.testlib.compare_html import compare_html
from tests.testlib.event_console import CMKEventConsole, CMKEventConsoleStatus
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import (
    add_python_paths,
    cmc_path,
    cme_path,
    cmk_path,
    current_branch_name,
    get_cmk_download_credentials,
    get_standard_linux_agent_output,
    is_cloud_repo,
    is_enterprise_repo,
    is_managed_repo,
    is_saas_repo,
    repo_path,
    site_id,
    virtualenv_path,
)
from tests.testlib.version import CMKVersion  # noqa: F401 # pylint: disable=unused-import
from tests.testlib.web_session import APIError, CMKWebSession

from cmk.utils.hostaddress import HostName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register.utils_legacy import LegacyCheckDefinition

# Disable insecure requests warning message during SSL testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def skip_unwanted_test_types(item: pytest.Item) -> None:
    test_type = item.get_closest_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)


_UNPATCHED_PATHS: Final = {
    # FIXME :-(
    # dropping these makes tests/unit/cmk/gui/watolib/test_config_sync.py fail.
    "local_dashboards_dir",
    "local_views_dir",
    "local_reports_dir",
}


# Some cmk.* code is calling things like cmk_version.is_raw_edition() at import time
# (e.g. cmk/base/default_config/notify.py) for edition specific variable
# defaults. In integration tests we want to use the exact version of the
# site. For unit tests we assume we are in Enterprise Edition context.
def fake_version_and_paths() -> None:
    from pytest import MonkeyPatch  # pylint: disable=import-outside-toplevel

    monkeypatch = MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    import cmk.utils.paths  # pylint: disable=import-outside-toplevel
    import cmk.utils.version as cmk_version  # pylint: disable=import-outside-toplevel

    if is_managed_repo():
        edition_short = "cme"
    elif is_cloud_repo():
        edition_short = "cce"
    elif is_saas_repo():
        edition_short = "cse"
    elif is_enterprise_repo():
        edition_short = "cee"
    else:
        edition_short = "cre"

    monkeypatch.setattr(cmk_version, "orig_omd_version", cmk_version.omd_version, raising=False)
    monkeypatch.setattr(
        cmk_version, "omd_version", lambda: f"{cmk_version.__version__}.{edition_short}"
    )

    # Unit test context: load all available modules
    original_omd_root = Path(cmk.utils.paths.omd_root)
    for name, value in vars(cmk.utils.paths).items():
        if name.startswith("_") or not isinstance(value, (str, Path)) or name in _UNPATCHED_PATHS:
            continue

        try:
            monkeypatch.setattr(
                f"cmk.utils.paths.{name}",
                type(value)(tmp_dir / Path(value).relative_to(original_omd_root)),
            )
        except ValueError:
            pass  # path is outside of omd_root

    # these use cmk_path
    monkeypatch.setattr("cmk.utils.paths.agents_dir", "%s/agents" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.checks_dir", "%s/checks" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.notifications_dir", Path(cmk_path()) / "notifications")
    monkeypatch.setattr("cmk.utils.paths.inventory_dir", "%s/inventory" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.legacy_check_manpages_dir", "%s/checkman" % cmk_path())
    monkeypatch.setattr("cmk.utils.paths.web_dir", "%s/web" % cmk_path())


def import_module_hack(pathname: str) -> ModuleType:
    """Return the module loaded from `pathname`.

    `pathname` is a path relative to the top-level directory
    of the repository.

    This function loads the module at `pathname` even if it does not have
    the ".py" extension.

    See: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    """
    name = os.path.splitext(os.path.basename(pathname))[0]
    location = os.path.join(cmk_path(), pathname)
    loader = importlib.machinery.SourceFileLoader(name, location)
    spec = importlib.machinery.ModuleSpec(name, loader, origin=location)
    spec.has_location = True
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def wait_until(condition: Callable[[], bool], timeout: float = 1, interval: float = 0.1) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise Exception("Timeout waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))


def wait_until_liveproxyd_ready(site: Site, site_ids: Collection[str]) -> None:
    def _config_available() -> bool:
        return site.file_exists("etc/check_mk/liveproxyd.mk")

    wait_until(_config_available, timeout=60, interval=0.5)

    # First wait for the site sockets to appear
    def _all_sockets_opened() -> bool:
        return all(site.file_exists("tmp/run/liveproxy/%s" % s) for s in site_ids)

    wait_until(_all_sockets_opened, timeout=60, interval=0.5)

    # Then wait for the sites to be ready
    def _all_sites_ready() -> bool:
        content = site.read_file("var/log/liveproxyd.state")
        num_ready = content.count("State:                   ready")
        print("%d sites are ready. Waiting for %d sites to be ready." % (num_ready, len(site_ids)))
        return len(site_ids) == num_ready

    wait_until(_all_sites_ready, timeout=60, interval=0.5)


class WatchLog:
    """Small helper for integration tests: Watch a sites log file"""

    def __init__(self, site: Site, default_timeout: int | None = None) -> None:
        self._site = site
        self._log_path = site.core_history_log()
        self._default_timeout = default_timeout or site.core_history_log_timeout()

        self._tail_process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "WatchLog":
        if not self._site.file_exists(self._log_path):
            self._site.write_text_file(self._log_path, "")

        self._tail_process = self._site.execute(
            ["tail", "-f", self._site.path(self._log_path)],
            stdout=subprocess.PIPE,
            bufsize=1,  # line buffered
        )

        # Make stdout non blocking. Otherwise the timeout handling
        # in _check_for_line will not work
        assert self._tail_process.stdout is not None
        fd = self._tail_process.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        return self

    def __exit__(self, *_exc_info: object) -> None:
        if self._tail_process is not None:
            for c in Process(self._tail_process.pid).children(recursive=True):
                if c.name() == "tail":
                    assert self._site.execute(["kill", str(c.pid)]).wait() == 0
            self._tail_process.wait()
            self._tail_process = None

    def check_logged(self, match_for: str, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = self._default_timeout
        found, lines = self._check_for_line(match_for, timeout)
        if not found:
            raise Exception(
                "Did not find %r in %s after %d seconds\n%s"
                % (match_for, self._log_path, timeout, lines)
            )

    def check_not_logged(self, match_for: str, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = self._default_timeout
        found, lines = self._check_for_line(match_for, timeout)
        if found:
            raise Exception(
                "Found %r in %s after %d seconds\n%s" % (match_for, self._log_path, timeout, lines)
            )

    def _check_for_line(self, match_for: str, timeout: float) -> tuple[bool, str]:
        if self._tail_process is None:
            raise Exception("no log file")
        timeout_at = time.time() + timeout
        sys.stdout.write(
            "Start checking for matching line %r at %d until %d\n"
            % (match_for, time.time(), timeout_at)
        )
        lines: list[str] = []
        while time.time() < timeout_at:
            # print("read till timeout %0.2f sec left" % (timeout_at - time.time()))
            assert self._tail_process.stdout is not None
            line = self._tail_process.stdout.readline()
            lines += line
            if line:
                sys.stdout.write("PROCESS LINE: %r\n" % line)
            if match_for in line:
                return True, "".join(lines)
            time.sleep(0.1)

        sys.stdout.write("Timed out at %d\n" % (time.time()))
        return False, "".join(lines)


def create_linux_test_host(request: pytest.FixtureRequest, site: Site, hostname: str) -> None:
    def get_data_source_cache_files(name: str) -> list[str]:
        p = site.execute(
            ["ls", f"tmp/check_mk/data_source_cache/*/{name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output = p.communicate()[0].strip()
        if not output:
            return []
        assert isinstance(output, str)
        return output.split(" ")

    def finalizer() -> None:
        site.openapi.delete_host(hostname)
        site.activate_changes_and_wait_for_core_reload()

        for path in [
            "var/check_mk/agent_output/%s" % hostname,
            "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
            "tmp/check_mk/status_data/%s" % hostname,
            "tmp/check_mk/status_data/%s.gz" % hostname,
            "var/check_mk/inventory/%s" % hostname,
            "var/check_mk/inventory/%s.gz" % hostname,
            "var/check_mk/autochecks/%s.mk" % hostname,
            "tmp/check_mk/counters/%s" % hostname,
            "tmp/check_mk/cache/%s" % hostname,
        ] + get_data_source_cache_files(hostname):
            if site.file_exists(path):
                site.delete_file(path)

    request.addfinalizer(finalizer)

    site.openapi.create_host(hostname, attributes={"ipaddress": "127.0.0.1"})

    site.write_text_file(
        "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
        f"datasource_programs.append({{'condition': {{'hostname': ['{hostname}']}}, 'value': 'cat ~/var/check_mk/agent_output/<HOST>'}})\n",
    )

    site.makedirs("var/check_mk/agent_output/")
    site.write_text_file(
        "var/check_mk/agent_output/%s" % hostname, get_standard_linux_agent_output()
    )


# .
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


class MissingCheckInfoError(KeyError):
    pass


class BaseCheck(abc.ABC):
    """Abstract base class for Check and ActiveCheck"""

    def __init__(self, name: str) -> None:
        self.name = name
        # we cant use the current_host context, b/c some tests rely on a persistent
        # item state across several calls to run_check
        import cmk.base.plugin_contexts  # pylint: disable=import-outside-toplevel

        cmk.base.plugin_contexts._hostname = HostName("non-existent-testhost")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"


class Check(BaseCheck):
    def __init__(self, name: str) -> None:
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel
        from cmk.base.api.agent_based import register  # pylint: disable=import-outside-toplevel

        super().__init__(name)
        if self.name not in config.check_info:
            raise MissingCheckInfoError(self.name)
        self.info: LegacyCheckDefinition = config.check_info[self.name]
        self._migrated_plugin = register.get_check_plugin(
            CheckPluginName(self.name.replace(".", "_"))
        )

    def default_parameters(self) -> Mapping[str, Any]:
        if self._migrated_plugin:
            return self._migrated_plugin.check_default_parameters or {}
        return {}

    def run_parse(self, info):  # type: ignore[no-untyped-def]
        parse_func = self.info.get("parse_function")
        if not parse_func:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no parse function defined")
        return parse_func(info)

    def run_discovery(self, info):  # type: ignore[no-untyped-def]
        disco_func = self.info.get("discovery_function")
        if not disco_func:
            raise MissingCheckInfoError(
                "Check '%s' " % self.name + "has no discovery function defined"
            )
        return disco_func(info)

    def run_check(self, item, params, info):  # type: ignore[no-untyped-def]
        check_func = self.info.get("check_function")
        if not check_func:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no check function defined")
        return check_func(item, params, info)


class ActiveCheck(BaseCheck):
    def __init__(self, name: str) -> None:
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel

        super().__init__(name)
        self.info = config.active_check_info.get(self.name[len("check_") :])

    def run_argument_function(self, params):  # type: ignore[no-untyped-def]
        assert self.info, "Active check has to be implemented in the legacy API"
        return self.info["argument_function"](params)

    def run_service_description(self, params):  # type: ignore[no-untyped-def]
        assert self.info, "Active check has to be implemented in the legacy API"
        return self.info["service_description"](params)

    def run_generate_icmp_services(self, host_config, params):  # type: ignore[no-untyped-def]
        assert self.info, "Active check has to be implemented in the legacy API"
        yield from self.info["service_generator"](host_config, params)


class SpecialAgent:
    def __init__(self, name: str) -> None:
        import cmk.base.config as config  # pylint: disable=import-outside-toplevel

        super().__init__()
        self.name = name
        assert self.name.startswith(
            "agent_"
        ), "Specify the full name of the active check, e.g. agent_3par"
        self.argument_func = config.special_agent_info[self.name[len("agent_") :]]


def _set_tz(timezone: str | None) -> str | None:
    old_tz = os.environ.get("TZ")
    if timezone is None:
        del os.environ["TZ"]
    else:
        os.environ["TZ"] = timezone
    time.tzset()
    return old_tz


@contextmanager
def set_timezone(timezone: str) -> Iterator[None]:
    old_tz = _set_tz(timezone)
    try:
        yield
    finally:
        _set_tz(old_tz)


@contextmanager
def on_time(utctime: datetime.datetime | str | int | float, timezone: str) -> Iterator[None]:
    """Set the time and timezone for the test"""
    if isinstance(utctime, (int, float)):
        utctime = datetime.datetime.fromtimestamp(utctime, tz=datetime.UTC)

    with set_timezone(timezone), freezegun.freeze_time(utctime):
        yield


__all__ = [
    "cmc_path",
    "cme_path",
    "cmk_path",
    "add_python_paths",
    "create_linux_test_host",
    "fake_version_and_paths",
    "skip_unwanted_test_types",
    "wait_until_liveproxyd_ready",
    "wait_until",
    "on_time",
    "set_timezone",
    "Site",
    "SiteFactory",
    "Check",
    "MissingCheckInfoError",
    "CMKEventConsole",
    "CMKEventConsoleStatus",
    "import_module_hack",
    "APIError",
    "CMKWebSession",
    "compare_html",
    "current_branch_name",
    "get_cmk_download_credentials",
    "repo_path",
    "site_id",
    "virtualenv_path",
]
