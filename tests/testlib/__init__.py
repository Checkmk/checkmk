#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import fcntl
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any, Final

import pytest
import urllib3
from psutil import Process

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import (
    add_python_paths,
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
    wait_until,
)
from tests.testlib.version import CMKVersion  # noqa: F401 # pylint: disable=unused-import
from tests.testlib.web_session import APIError, CMKWebSession

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

    # these use repo_path
    monkeypatch.setattr("cmk.utils.paths.agents_dir", "%s/agents" % repo_path())
    monkeypatch.setattr("cmk.utils.paths.checks_dir", "%s/checks" % repo_path())
    monkeypatch.setattr("cmk.utils.paths.notifications_dir", repo_path() / "notifications")
    monkeypatch.setattr("cmk.utils.paths.inventory_dir", "%s/inventory" % repo_path())
    monkeypatch.setattr("cmk.utils.paths.legacy_check_manpages_dir", "%s/checkman" % repo_path())


def import_module_hack(pathname: str) -> ModuleType:
    """Return the module loaded from `pathname`.

    `pathname` is a path relative to the top-level directory
    of the repository.

    This function loads the module at `pathname` even if it does not have
    the ".py" extension.

    See: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    """
    name = os.path.splitext(os.path.basename(pathname))[0]
    location = os.path.join(repo_path(), pathname)
    loader = importlib.machinery.SourceFileLoader(name, location)
    spec = importlib.machinery.ModuleSpec(name, loader, origin=location)
    spec.has_location = True
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
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
                "Did not find %r in %s after %d seconds\n'%s'"
                % (match_for, self._log_path, timeout, lines)
            )

    def check_not_logged(self, match_for: str, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = self._default_timeout
        found, lines = self._check_for_line(match_for, timeout)
        if found:
            raise Exception(
                "Found %r in %s after %d seconds\n'%s'"
                % (match_for, self._log_path, timeout, lines)
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


__all__ = [
    "repo_path",
    "add_python_paths",
    "create_linux_test_host",
    "fake_version_and_paths",
    "skip_unwanted_test_types",
    "wait_until_liveproxyd_ready",
    "set_timezone",
    "Site",
    "SiteFactory",
    "import_module_hack",
    "APIError",
    "CMKWebSession",
    "current_branch_name",
    "get_cmk_download_credentials",
    "site_id",
    "virtualenv_path",
]
