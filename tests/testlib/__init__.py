#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from __future__ import print_function

import os
import sys
import tempfile
import time

from pathlib2 import Path
import urllib3  # type: ignore[import]

from testlib.utils import (
    cmk_path,
    is_running_as_site_user,
    is_enterprise_repo,
    is_managed_repo,
    get_standard_linux_agent_output,
)

# Disable insecure requests warning message during SSL testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Some cmk.* code is calling things like cmk_version.is_raw_edition() at import time
# (e.g. cmk/base/default_config/notify.py) for edition specific variable
# defaults. In integration tests we want to use the exact version of the
# site. For unit tests we assume we are in Enterprise Edition context.
def fake_version_and_paths():
    if is_running_as_site_user():
        return

    import _pytest.monkeypatch  # type: ignore
    monkeypatch = _pytest.monkeypatch.MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    import cmk.utils.version as cmk_version
    import cmk.utils.paths

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


def wait_until(condition, timeout=1, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise Exception("Timeout out waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))


class WatchLog(object):
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
