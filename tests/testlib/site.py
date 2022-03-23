#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import glob
import logging
import os
import pipes
import pwd
import shutil
import subprocess
import sys
import time
import urllib.parse
from contextlib import suppress
from pathlib import Path
from typing import List, Literal, Mapping, MutableMapping, Optional, Union

import pytest

from tests.testlib.openapi_session import CMKOpenApiSession
from tests.testlib.utils import (
    cmc_path,
    cme_path,
    cmk_path,
    current_base_branch_name,
    virtualenv_path,
)
from tests.testlib.version import CMKVersion
from tests.testlib.web_session import CMKWebSession

import livestatus

logger = logging.getLogger(__name__)

PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR = sys.version_info.major, sys.version_info.minor


class Site:
    def __init__(
        self,
        site_id: str,
        reuse: bool = True,
        version: str = CMKVersion.DEFAULT,
        edition: str = CMKVersion.CEE,
        branch: str = "master",
        update_from_git: bool = False,
        install_test_python_modules: bool = True,
        admin_password: str = "cmk",
    ) -> None:
        assert site_id
        self.id = site_id
        self.root = "/omd/sites/%s" % self.id
        self.version = CMKVersion(version, edition, branch)

        self.update_from_git = update_from_git
        self.install_test_python_modules = install_test_python_modules

        self.reuse = reuse

        self.http_proto = "http"
        self.http_address = "127.0.0.1"
        self._apache_port: Optional[int] = None  # internal cache for the port

        self._livestatus_port: Optional[int] = None
        self.admin_password = admin_password

        self.openapi = CMKOpenApiSession(
            host=self.http_address,
            port=self.apache_port if self.exists() else 80,
            user="automation" if self.exists() else "cmkadmin",
            password=self.get_automation_secret() if self.exists() else self.admin_password,
            site=self.id,
        )

    @property
    def apache_port(self) -> int:
        if self._apache_port is None:
            self._apache_port = int(self.get_config("APACHE_TCP_PORT"))
        return self._apache_port

    @property
    def internal_url(self) -> str:
        """This gives the address-port combination where the site-Apache process listens."""
        return f"{self.http_proto}://{self.http_address}:{self.apache_port}/{self.id}/check_mk/"

    # Previous versions of integration/composition tests needed this distinction. This is no
    # longer the case and can be safely removed once all tests switch to either one of url
    # or internal_url.
    url = internal_url

    @property
    def livestatus_port(self) -> int:
        if self._livestatus_port is None:
            raise Exception("Livestatus TCP not opened yet")
        return self._livestatus_port

    @property
    def live(self) -> livestatus.SingleSiteConnection:
        # Note: If the site comes from a SiteFactory instance, the TCP connection
        # is insecure, i.e. no TLS.
        live = (
            livestatus.LocalConnection()
            if self._is_running_as_site_user()
            else livestatus.SingleSiteConnection(
                "tcp:%s:%d" % (self.http_address, self.livestatus_port)
            )
        )
        live.set_timeout(2)
        return live

    def url_for_path(self, path: str) -> str:
        """
        Computes a full URL inkl. http://... from a URL starting with the path.
        In case no path component is in URL, prepend "/[site]/check_mk" to the path.
        """
        assert not path.startswith("http")
        assert "://" not in path

        if "/" not in urllib.parse.urlparse(path).path:
            path = "/%s/check_mk/%s" % (self.id, path)
        return f"{self.http_proto}://{self.http_address}:{self.apache_port}{path}"

    def wait_for_core_reloaded(self, after) -> None:
        # Activating changes can involve an asynchronous(!) monitoring
        # core restart/reload, so e.g. querying a Livestatus table immediately
        # might not reflect the changes yet. Ask the core for a successful reload.
        def config_reloaded():
            try:
                new_t = self.live.query_value("GET status\nColumns: program_start\n")
            except livestatus.MKLivestatusException:
                # Seems like the socket may vanish for a short time. Keep waiting in case
                # of livestatus (connection) issues...
                return False
            return new_t > after

        reload_time, timeout = time.time(), 40
        while not config_reloaded():
            if time.time() > reload_time + timeout:
                raise Exception("Config did not update within %d seconds" % timeout)
            time.sleep(0.2)

        assert config_reloaded()

    def restart_core(self) -> None:
        # Remember the time for the core reload check and wait a second because the program_start
        # is reported as integer and wait_for_core_reloaded() compares with ">".
        before_restart = time.time()
        time.sleep(1)
        self.omd("restart", "core")
        self.wait_for_core_reloaded(before_restart)

    def send_host_check_result(
        self, hostname: str, state: int, output: str, expected_state: Optional[int] = None
    ) -> None:
        if expected_state is None:
            expected_state = state
        last_check_before = self._last_host_check(hostname)
        command_timestamp = self._command_timestamp(last_check_before)
        self.live.command(
            f"[{command_timestamp:.0f}] PROCESS_HOST_CHECK_RESULT;{hostname};{state};{output}"
        )
        self._wait_for_next_host_check(
            hostname, last_check_before, command_timestamp, expected_state
        )

    def send_service_check_result(
        self,
        hostname: str,
        service_description: str,
        state: int,
        output: str,
        expected_state: Optional[int] = None,
    ) -> None:
        if expected_state is None:
            expected_state = state
        last_check_before = self._last_service_check(hostname, service_description)
        command_timestamp = self._command_timestamp(last_check_before)
        self.live.command(
            f"[{command_timestamp:.0f}] PROCESS_SERVICE_CHECK_RESULT;{hostname};{service_description};{state};{output}"
        )
        self._wait_for_next_service_check(
            hostname, service_description, last_check_before, command_timestamp, expected_state
        )

    def schedule_check(self, hostname: str, service_description: str, expected_state: int) -> None:
        logger.debug("%s;%s schedule check", hostname, service_description)
        last_check_before = self._last_service_check(hostname, service_description)
        logger.debug("%s;%s last check before %r", hostname, service_description, last_check_before)

        command_timestamp = self._command_timestamp(last_check_before)

        command = f"[{command_timestamp:.0f}] SCHEDULE_FORCED_SVC_CHECK;{hostname};{service_description};{command_timestamp:.0f}"

        logger.debug("%s;%s: %r", hostname, service_description, command)
        self.live.command(command)

        self._wait_for_next_service_check(
            hostname, service_description, last_check_before, command_timestamp, expected_state
        )

    def _command_timestamp(self, last_check_before: float) -> float:
        # Ensure the next check result is not in same second as the previous check
        timestamp = time.time()
        while int(last_check_before) == int(timestamp):
            timestamp = time.time()
            time.sleep(0.1)
        return timestamp

    def _wait_for_next_host_check(
        self, hostname: str, last_check_before: float, command_timestamp: float, expected_state: int
    ) -> None:
        wait_timeout = 20
        last_check, state, plugin_output = self.live.query_row(
            "GET hosts\n"
            "Columns: last_check state plugin_output\n"
            f"Filter: host_name = {hostname}\n"
            f"WaitObject: {hostname}\n"
            f"WaitTimeout: {wait_timeout*1000:d}\n"
            f"WaitCondition: last_check > {last_check_before:.0f}\n"
            f"WaitCondition: state = {expected_state}\n"
            "WaitTrigger: check\n"
        )
        self._verify_next_check_output(
            command_timestamp,
            last_check,
            last_check_before,
            state,
            expected_state,
            plugin_output,
            wait_timeout,
        )

    def _wait_for_next_service_check(
        self,
        hostname: str,
        service_description: str,
        last_check_before: float,
        command_timestamp: float,
        expected_state: int,
    ) -> None:
        wait_timeout = 20
        last_check, state, plugin_output = self.live.query_row(
            "GET services\n"
            "Columns: last_check state plugin_output\n"
            f"Filter: host_name = {hostname}\n"
            f"Filter: description = {service_description}\n"
            f"WaitObject: {hostname};{service_description}\n"
            f"WaitTimeout: {wait_timeout*1000:d}\n"
            f"WaitCondition: last_check > {last_check_before:.0f}\n"
            f"WaitCondition: state = {expected_state}\n"
            "WaitCondition: has_been_checked = 1\n"
            "WaitTrigger: check\n"
        )
        self._verify_next_check_output(
            command_timestamp,
            last_check,
            last_check_before,
            state,
            expected_state,
            plugin_output,
            wait_timeout,
        )

    def _verify_next_check_output(
        self,
        command_timestamp: float,
        last_check: float,
        last_check_before: float,
        state: int,
        expected_state: int,
        plugin_output: str,
        wait_timeout: int,
    ) -> None:
        logger.debug("processing check result took %0.2f seconds", time.time() - command_timestamp)
        assert last_check > last_check_before, (
            f"Check result not processed within {wait_timeout} seconds "
            f"(last check before reschedule: {last_check_before:.0f}, "
            f"scheduled at: {command_timestamp:.0f}, last check: {last_check:.0f})"
        )
        assert (
            state == expected_state
        ), f"Expected {expected_state} state, got {state} state, output {plugin_output}"

    def _last_host_check(self, hostname: str) -> float:
        return self.live.query_value(
            f"GET hosts\nColumns: last_check\nFilter: host_name = {hostname}\n"
        )

    def _last_service_check(self, hostname: str, service_description: str) -> float:
        return self.live.query_value(
            "GET services\n"
            "Columns: last_check\n"
            f"Filter: host_name = {hostname}\n"
            f"Filter: service_description = {service_description}\n"
        )

    def get_host_state(self, hostname: str) -> int:
        return self.live.query_value(f"GET hosts\nColumns: state\nFilter: host_name = {hostname}")

    def _is_running_as_site_user(self) -> bool:
        return pwd.getpwuid(os.getuid()).pw_name == self.id

    def execute(self, cmd: List[str], *args, **kwargs) -> subprocess.Popen:
        assert isinstance(cmd, list), "The command must be given as list"

        kwargs.setdefault("encoding", "utf-8")
        cmd_txt = (
            subprocess.list2cmdline(cmd)
            if self._is_running_as_site_user()
            else " ".join(  #
                [
                    "sudo",
                    "su",
                    "-l",
                    self.id,
                    "-c",
                    pipes.quote(" ".join(pipes.quote(p) for p in cmd)),
                ]
            )
        )
        logger.info("Executing: %s", cmd_txt)
        kwargs["shell"] = True
        return subprocess.Popen(cmd_txt, *args, **kwargs)

    def omd(self, mode: str, *args: str) -> int:
        sudo, site_id = ([], []) if self._is_running_as_site_user() else (["sudo"], [self.id])
        cmd = sudo + ["/usr/bin/omd", mode] + site_id + list(args)
        logger.info("Executing: %s", subprocess.list2cmdline(cmd))
        completed_process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )

        log_level = logging.DEBUG if completed_process.returncode == 0 else logging.WARNING
        logger.log(log_level, "Exit code: %d", completed_process.returncode)
        if completed_process.stdout:
            logger.log(log_level, "Output:")
        for line in completed_process.stdout.strip().split("\n"):
            logger.log(log_level, "> %s", line)

        return completed_process.returncode

    def path(self, rel_path: str) -> str:
        return os.path.join(self.root, rel_path)

    def read_file(self, rel_path: str) -> str:
        if not self._is_running_as_site_user():
            p = self.execute(["cat", self.path(rel_path)], stdout=subprocess.PIPE)
            if p.wait() != 0:
                raise Exception("Failed to read file %s. Exit-Code: %d" % (rel_path, p.wait()))
            return p.stdout.read() if p.stdout is not None else ""
        return open(self.path(rel_path)).read()

    def delete_file(self, rel_path: str, missing_ok: bool = False) -> None:
        if not self._is_running_as_site_user():
            p = self.execute(["rm", "-f", self.path(rel_path)])
            if p.wait() != 0:
                raise Exception("Failed to delete file %s. Exit-Code: %d" % (rel_path, p.wait()))
        else:
            Path(self.path(rel_path)).unlink(missing_ok=missing_ok)

    def delete_dir(self, rel_path: str) -> None:
        if not self._is_running_as_site_user():
            p = self.execute(["rm", "-rf", self.path(rel_path)])
            if p.wait() != 0:
                raise Exception(
                    "Failed to delete directory %s. Exit-Code: %d" % (rel_path, p.wait())
                )
        else:
            shutil.rmtree(self.path(rel_path))

    def _call_tee(self, rel_target_path: str, content: Union[bytes, str]) -> None:
        with self.execute(
            ["tee", self.path(rel_target_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            encoding=None
            if isinstance(
                content,
                bytes,
            )
            else "utf-8",
        ) as p:
            p.communicate(content)
        if p.returncode != 0:
            raise Exception(
                "Failed to write file %s. Exit-Code: %d"
                % (
                    rel_target_path,
                    p.returncode,
                )
            )

    def write_text_file(self, rel_path: str, content: str) -> None:
        if not self._is_running_as_site_user():
            self._call_tee(rel_path, content)
        else:
            file_path = Path(self.path(rel_path))
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as f:
                f.write(content)

    def write_binary_file(self, rel_path: str, content: bytes) -> None:
        if not self._is_running_as_site_user():
            self._call_tee(rel_path, content)
        else:
            file_path = Path(self.path(rel_path))
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("wb") as f:
                f.write(content)

    def create_rel_symlink(self, link_rel_target: str, rel_link_name: str) -> None:
        if not self._is_running_as_site_user():
            with self.execute(
                ["ln", "-s", link_rel_target, rel_link_name],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
            ) as p:
                p.wait()
            if p.returncode != 0:
                raise Exception(
                    "Failed to create symlink from %s to ./%s. Exit-Code: %d"
                    % (rel_link_name, link_rel_target, p.returncode)
                )
        else:
            os.symlink(link_rel_target, os.path.join(self.root, rel_link_name))

    def resolve_path(self, rel_path: Path) -> Path:
        if not self._is_running_as_site_user():
            p = self.execute(["readlink", "-e", self.path(str(rel_path))], stdout=subprocess.PIPE)
            if p.wait() != 0:
                raise Exception(f"Failed to read symlink at {rel_path}. Exit-Code: {p.wait()}")
            if p.stdout is None:
                raise Exception(f"Failed to read symlink at {rel_path}. No stdout.")
            return Path(p.stdout.read().strip())
        return Path(self.path(str(rel_path))).resolve()

    def file_exists(self, rel_path: str) -> bool:
        if not self._is_running_as_site_user():
            p = self.execute(["test", "-e", self.path(rel_path)], stdout=subprocess.PIPE)
            return p.wait() == 0

        return os.path.exists(self.path(rel_path))

    def makedirs(self, rel_path: str) -> bool:
        p = self.execute(["mkdir", "-p", self.path(rel_path)])
        return p.wait() == 0

    def cleanup_if_wrong_version(self) -> None:
        if not self.exists():
            return

        if self.current_version_directory() == self.version.version_directory():
            return

        # Now cleanup!
        self.rm()

    def current_version_directory(self) -> str:
        return os.path.split(os.readlink("/omd/sites/%s/version" % self.id))[-1]

    def create(self) -> None:
        if not self.version.is_installed():
            raise Exception(
                "Version %s not installed. "
                'Use "tests/scripts/install-cmk.py" or install it manually.' % self.version.version
            )

        if not self.reuse and self.exists():
            raise Exception("The site %s already exists." % self.id)

        if not self.exists():
            logger.info("Creating site '%s'", self.id)
            completed_process = subprocess.run(
                [
                    "/usr/bin/sudo",
                    "/usr/bin/omd",
                    "-V",
                    self.version.version_directory(),
                    "create",
                    "--admin-password",
                    self.admin_password,
                    "--apache-reload",
                    self.id,
                ],
                check=False,
            )
            assert completed_process.returncode == 0
            assert os.path.exists("/omd/sites/%s" % self.id)

            self._ensure_sample_config_is_present()
            if not self.version.is_raw_edition():
                self._log_cmc_startup()
                self._enable_cmc_core_dumps()
                self._enable_cmc_debug_logging()
                self._disable_cmc_log_rotation()
                self._enabled_liveproxyd_debug_logging()
            self._enable_mkeventd_debug_logging()
            self._enable_gui_debug_logging()
            self._tune_nagios()

        if self.install_test_python_modules:
            self._install_test_python_modules()

        if self.update_from_git:
            self._update_with_f12_files()

        # The tmpfs is already mounted during "omd create". We have just created some
        # Checkmk configuration files and want to be sure they are used once the core
        # starts.
        self._update_cmk_core_config()

        self.makedirs(self.result_dir())

        self.openapi.port = self.apache_port
        self.openapi.set_authentication_header(
            user="automation", password=self.get_automation_secret()
        )

    def _ensure_sample_config_is_present(self) -> None:
        if missing_files := self._missing_but_required_wato_files():
            raise Exception(
                "Sample config was not created by post create hook "
                "01_create-sample-config.py (Missing files: %s)" % missing_files
            )

    def _missing_but_required_wato_files(self) -> List[str]:
        required_files = [
            "etc/check_mk/conf.d/wato/rules.mk",
            "etc/check_mk/multisite.d/wato/tags.mk",
            "etc/check_mk/conf.d/wato/global.mk",
            "var/check_mk/web/automation",
            "var/check_mk/web/automation/automation.secret",
        ]

        missing = []
        for f in required_files:
            if not self.file_exists(f):
                missing.append(f)
        return missing

    def _update_with_f12_files(self) -> None:
        paths = [
            cmk_path() + "/omd/packages/omd",
            cmk_path() + "/livestatus/api/python",
            cmk_path() + "/bin",
            cmk_path() + "/agents/special",
            cmk_path() + "/agents/plugins",
            cmk_path() + "/agents/windows/plugins",
            cmk_path() + "/agents",
            cmk_path() + "/cmk/base",
            cmk_path() + "/cmk",
            cmk_path() + "/checks",
            cmk_path() + "/checkman",
            cmk_path() + "/web",
            cmk_path() + "/inventory",
            cmk_path() + "/notifications",
            cmk_path() + "/.werks",
        ]

        if self.version.is_raw_edition():
            # The module is only used in CRE
            paths += [
                cmk_path() + "/livestatus",
            ]

        if os.path.exists(cmc_path()) and not self.version.is_raw_edition():
            paths += [
                cmc_path() + "/bin",
                cmc_path() + "/agents/plugins",
                cmc_path() + "/modules",
                cmc_path() + "/cmk/base",
                cmc_path() + "/cmk",
                cmc_path() + "/web",
                cmc_path() + "/alert_handlers",
                cmc_path() + "/misc",
                cmc_path() + "/core",
                # TODO: Do not invoke the chroot build mechanism here, which is very time
                # consuming when not initialized yet
                # cmc_path() + "/agents",
            ]

        if os.path.exists(cme_path()) and self.version.is_managed_edition():
            paths += [
                cme_path(),
                cme_path() + "/cmk/base",
            ]

        for path in paths:
            if os.path.exists("%s/.f12" % path):
                logger.info('Executing .f12 in "%s"...', path)
                assert (
                    os.system(  # nosec
                        'cd "%s" ; '
                        "sudo PATH=$PATH ONLY_COPY=1 ALL_EDITIONS=0 SITE=%s "
                        "CHROOT_BASE_PATH=$CHROOT_BASE_PATH CHROOT_BUILD_DIR=$CHROOT_BUILD_DIR "
                        "bash .f12" % (path, self.id)
                    )
                    >> 8
                    == 0
                )
                logger.info('Executing .f12 in "%s" DONE', path)

    def _update_cmk_core_config(self) -> None:
        logger.info("Updating core configuration...")
        p = self.execute(["cmk", "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert p.wait() == 0, "Failed to execute 'cmk -U': %s" % p.communicate()[0]

    def _enabled_liveproxyd_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/liveproxyd.d")
        # 15 = verbose
        # 10 = debug
        self.write_text_file(
            "etc/check_mk/liveproxyd.d/logging.mk", "liveproxyd_log_levels = {'cmk.liveproxyd': 15}"
        )

    def _enable_mkeventd_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/mkeventd.d")
        self.write_text_file(
            "etc/check_mk/mkeventd.d/logging.mk",
            "log_level = %r\n"
            % {
                "cmk.mkeventd": 10,
                "cmk.mkeventd.EventServer": 10,
                "cmk.mkeventd.EventServer.snmp": 10,
                "cmk.mkeventd.EventStatus": 10,
                "cmk.mkeventd.StatusServer": 10,
                "cmk.mkeventd.lock": 20,
            },
        )

    def _log_cmc_startup(self):
        tool = None  # sensible tools for us: None, "memcheck" or "helgrind"
        valgrind = (
            'PATH="/opt/bin:$PATH" '
            f"valgrind --tool={tool} --quiet --num-callers=30 --error-exitcode=42 --exit-on-first-error=yes"
        )
        redirect = ">> $OMD_ROOT/var/log/cmc-startup.log 2>&1"
        self.write_text_file(
            "etc/init.d/cmc",
            self.read_file("etc/init.d/cmc").replace(
                "\n    if $DAEMON $CONFIGFILE; then\n",
                "\n"  #
                f"    date {redirect}\n"  #
                f"    ps -fu {self.id} {redirect}\n"
                f"    if {valgrind if tool else ''} $DAEMON $CONFIGFILE {redirect}; then\n",
            ),
        )

    def _enable_cmc_core_dumps(self) -> None:
        self.makedirs("etc/check_mk/conf.d")
        self.write_text_file("etc/check_mk/conf.d/cmc-core-dumps.mk", "cmc_dump_core = True\n")

    def _enable_cmc_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/conf.d")
        self.write_text_file(
            "etc/check_mk/conf.d/cmc-debug-logging.mk",
            "cmc_log_levels = %r\n"
            % {
                "cmk.alert": 7,
                "cmk.carbon": 7,
                "cmk.core": 7,
                "cmk.downtime": 7,
                "cmk.helper": 6,
                "cmk.livestatus": 7,
                "cmk.notification": 7,
                "cmk.rrd": 7,
                "cmk.influxdb": 7,
                "cmk.smartping": 7,
            },
        )

    def _disable_cmc_log_rotation(self) -> None:
        self.makedirs("etc/check_mk/conf.d")
        self.write_text_file(
            "etc/check_mk/conf.d/cmc-log-rotation.mk",
            "cmc_log_rotation_method = 4\ncmc_log_limit = 1073741824\n",
        )

    def _enable_gui_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/multisite.d")
        self.write_text_file(
            "etc/check_mk/multisite.d/logging.mk",
            "log_levels = %r\n"
            % {
                "cmk.web": 10,
                "cmk.web.ldap": 10,
                "cmk.web.auth": 10,
                "cmk.web.bi.compilation": 10,
                "cmk.web.automations": 10,
                "cmk.web.background-job": 10,
            },
        )

    def _tune_nagios(self) -> None:
        self.write_text_file(
            "etc/nagios/nagios.d/zzz-test-tuning.cfg",
            # We need to observe these entries with WatchLog for our tests
            "log_passive_checks=1\n"
            # We want nagios to process queued external commands as fast as possible.  Even if we
            # set command_check_interval to -1, nagios is doing some sleeping in between the
            # command processing. We reduce the sleep time here to make it a little faster.
            "service_inter_check_delay_method=n\n"
            "host_inter_check_delay_method=n\n"
            "sleep_time=0.05\n"
            # WatchLog is not able to handle log rotations. Disable the rotation during tests.
            "log_rotation_method=n\n",
        )

    def _install_test_python_modules(self) -> None:
        venv = virtualenv_path()
        bin_dir = venv / "bin"
        self._copy_python_modules_from(
            venv / f"lib/python{PYTHON_VERSION_MAJOR}.{PYTHON_VERSION_MINOR}/site-packages"
        )

        # Some distros have a separate platfrom dependent library directory, handle it....
        platlib64 = (
            venv / f"lib64/python{PYTHON_VERSION_MAJOR}.{PYTHON_VERSION_MINOR}/site-packages"
        )
        if platlib64.exists():
            self._copy_python_modules_from(platlib64)

        for file_name in ["py.test", "pytest"]:
            assert (
                os.system(  # nosec
                    "sudo rsync -a --chown %s:%s %s %s/local/bin"
                    % (self.id, self.id, bin_dir / file_name, self.root)
                )
                >> 8
                == 0
            )

    def _copy_python_modules_from(self, packages_dir: Path) -> None:
        enforce_override = ["backports"]

        for file_name in os.listdir(str(packages_dir)):
            # Only copy modules that do not exist in regular module path
            if file_name not in enforce_override:
                if os.path.exists("%s/lib/python/%s" % (self.root, file_name)) or os.path.exists(
                    f"{self.root}/lib/python{PYTHON_VERSION_MAJOR}.{PYTHON_VERSION_MINOR}/site-packages/{file_name}"
                ):
                    continue

            assert (
                os.system(  # nosec
                    f"sudo rsync -a --chown {self.id}:{self.id} {packages_dir / file_name} {self.root}/local/lib/python{PYTHON_VERSION_MAJOR}/"
                )
                >> 8
                == 0
            )

    def rm(self, site_id: Optional[str] = None) -> None:
        # TODO: LM: Temporarily disabled until "omd rm" issue is fixed.
        # assert subprocess.Popen(["/usr/bin/sudo", "/usr/bin/omd",
        subprocess.run(
            [
                "/usr/bin/sudo",
                "/usr/bin/omd",
                "-f",
                "rm",
                "--apache-reload",
                "--kill",
                site_id or self.id,
            ],
            check=False,
        )

    def start(self) -> None:
        if not self.is_running():
            assert self.omd("start") == 0
            # print("= BEGIN PROCESSES AFTER START ==============================")
            # self.execute(["ps", "aux"]).wait()
            # print("= END PROCESSES AFTER START ==============================")
            i = 0
            while not self.is_running():
                i += 1
                if i > 10:
                    self.execute(["/usr/bin/omd", "status"]).wait()
                    # print("= BEGIN PROCESSES FAIL ==============================")
                    # self.execute(["ps", "aux"]).wait()
                    # print("= END PROCESSES FAIL ==============================")
                    logger.warning("Could not start site %s. Stop waiting.", self.id)
                    break
                logger.warning("The site %s is not running yet, sleeping... (round %d)", self.id, i)
                sys.stdout.flush()
                time.sleep(0.2)

            self.ensure_running()

        assert os.path.ismount(
            self.path("tmp")
        ), "The site does not have a tmpfs mounted! We require this for good performing tests"

    def stop(self) -> None:
        if self.is_stopped():
            return  # Nothing to do

        # logger.debug("= BEGIN PROCESSES BEFORE =======================================")
        # os.system("ps -fwwu %s" % self.id)  # nosec
        # logger.debug("= END PROCESSES BEFORE =======================================")

        stop_exit_code = self.omd("stop")
        if stop_exit_code != 0:
            logger.error("omd stop exit code: %d", stop_exit_code)

        # logger.debug("= BEGIN PROCESSES AFTER STOP =======================================")
        # os.system("ps -fwwu %s" % self.id)  # nosec
        # logger.debug("= END PROCESSES AFTER STOP =======================================")

        i = 0
        while not self.is_stopped():
            i += 1
            if i > 10:
                raise Exception("Could not stop site %s" % self.id)
            logger.warning("The site %s is still running, sleeping... (round %d)", self.id, i)
            sys.stdout.flush()
            time.sleep(0.2)

    def exists(self) -> bool:
        return os.path.exists("/omd/sites/%s" % self.id)

    def ensure_running(self) -> None:
        if not self.is_running():
            pytest.exit("Site was not running completely while it should. Enforcing stop.")

    def is_running(self) -> bool:
        return (
            self.execute(["/usr/bin/omd", "status", "--bare"], stdout=subprocess.DEVNULL).wait()
            == 0
        )

    def is_stopped(self) -> bool:
        # 0 -> fully running
        # 1 -> fully stopped
        # 2 -> partially running
        return (
            self.execute(["/usr/bin/omd", "status", "--bare"], stdout=subprocess.DEVNULL).wait()
            == 1
        )

    def set_config(self, key: str, val: str, with_restart: bool = False) -> None:
        if self.get_config(key) == val:
            logger.info("omd config: %s is already at %r", key, val)
            return

        if with_restart:
            logger.debug("Stopping site")
            self.stop()

        logger.info("omd config: Set %s to %r", key, val)
        assert self.omd("config", "set", key, val) == 0

        if with_restart:
            self.start()
            logger.debug("Started site")

    def get_config(self, key: str) -> str:
        p = self.execute(
            ["omd", "config", "show", key], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        logger.debug("omd config: %s is set to %r", key, stdout.strip())
        if stderr:
            logger.error(stderr)
        return stdout.strip()

    def core_name(self) -> Literal["cmc", "nagios"]:
        return "nagios" if self.version.is_raw_edition() else "cmc"

    def core_history_log(self) -> str:
        core = self.core_name()
        if core == "nagios":
            return "var/log/nagios.log"
        if core == "cmc":
            return "var/check_mk/core/history"
        raise ValueError(f"Unhandled core: {core}")

    def core_history_log_timeout(self) -> int:
        return 10 if self.core_name() == "cmc" else 30

    # These things are needed to make the site basically being setup. So this
    # is checked during site initialization instead of a dedicated test.
    def verify_cmk(self) -> None:
        p = self.execute(
            ["cmk", "--help"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True
        )
        stdout = p.communicate()[0]
        assert p.returncode == 0, "Failed to execute 'cmk': %s" % stdout

        p = self.execute(
            ["cmk", "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True
        )
        stdout = p.communicate()[0]
        assert p.returncode == 0, "Failed to execute 'cmk -U': %s" % stdout

    def prepare_for_tests(self) -> None:
        self.verify_cmk()

        web = CMKWebSession(self)
        web.login()
        web.enforce_non_localized_gui()
        self._add_wato_test_config(web)

    # Add some test configuration that is not test specific. These settings are set only to have a
    # bit more complex Checkmk config.
    def _add_wato_test_config(self, web: CMKWebSession) -> None:
        # This entry is interesting because it is a check specific setting. These
        # settings are only registered during check loading. In case one tries to
        # load the config without loading the checks in advance, this leads into an
        # exception.
        # We set this config option here trying to catch this kind of issue.
        web.set_ruleset(
            "fileinfo_groups",
            {
                "ruleset": {
                    "": [  # "" -> folder
                        {
                            "condition": {},
                            "options": {},
                            "value": {"group_patterns": [("TESTGROUP", ("*gwia*", ""))]},
                        },
                    ],
                }
            },
        )

    def open_livestatus_tcp(self, encrypted: bool) -> None:
        """This opens a currently free TCP port and remembers it in the object for later use
        Not free of races, but should be sufficient."""
        start_again = False

        if not self.is_stopped():
            start_again = True
            self.stop()

        logger.info("Have livestatus port lock")
        self.set_config("LIVESTATUS_TCP", "on")
        self._gather_livestatus_port()
        self.set_config("LIVESTATUS_TCP_PORT", str(self._livestatus_port))
        self.set_config("LIVESTATUS_TCP_TLS", "on" if encrypted else "off")

        if start_again:
            self.start()

        logger.info("After livestatus port lock")

    def _gather_livestatus_port(self) -> None:
        if self.reuse and self.exists():
            port = int(self.get_config("LIVESTATUS_TCP_PORT"))
        else:
            port = self.get_free_port_from(9123)

        self._livestatus_port = port

    def get_free_port_from(self, port: int) -> int:
        used_ports = set([])
        for cfg_path in Path("/omd/sites").glob("*/etc/omd/site.conf"):
            with cfg_path.open() as cfg_file:
                for line in cfg_file:
                    if line.startswith("CONFIG_LIVESTATUS_TCP_PORT="):
                        port = int(line.strip().split("=", 1)[1].strip("'"))
                        used_ports.add(port)

        while port in used_ports:
            port += 1

        logger.debug("Livestatus ports already in use: %r, using port: %d", used_ports, port)
        return port

    def save_results(self) -> None:
        if not _is_dockerized():
            logger.info("Not dockerized: not copying results")
            return
        logger.info("Saving to %s", self.result_dir())

        os.makedirs(self.result_dir(), exist_ok=True)

        with suppress(FileNotFoundError):
            shutil.copy(self.path("junit.xml"), self.result_dir())

        shutil.copytree(
            self.path("var/log"),
            "%s/logs" % self.result_dir(),
            ignore_dangling_symlinks=True,
            ignore=shutil.ignore_patterns(".*"),
        )

        for nagios_log_path in glob.glob(self.path("var/nagios/*.log")):
            shutil.copy(nagios_log_path, "%s/logs" % self.result_dir())

        cmc_dir = "%s/cmc" % self.result_dir()
        os.makedirs(cmc_dir, exist_ok=True)

        with suppress(FileNotFoundError):
            shutil.copy(self.path("var/check_mk/core/history"), "%s/history" % cmc_dir)

        with suppress(FileNotFoundError):
            shutil.copy(self.path("var/check_mk/core/core"), "%s/core_dump" % cmc_dir)

        with suppress(FileNotFoundError):
            shutil.copytree(
                self.path("var/check_mk/crashes"),
                "%s/crashes" % self.result_dir(),
                ignore=shutil.ignore_patterns(".*"),
            )

    def result_dir(self) -> str:
        return os.path.join(os.environ.get("RESULT_PATH", self.path("results")), self.id)

    def get_automation_secret(self):
        secret_path = "var/check_mk/web/automation/automation.secret"
        secret = self.read_file(secret_path).strip()

        if secret == "":
            raise Exception("Failed to read secret from %s" % secret_path)

        return secret

    def activate_changes_and_wait_for_core_reload(
        self, allow_foreign_changes: bool = False, remote_site: Optional["Site"] = None
    ):
        self.ensure_running()
        site = remote_site or self

        logger.debug("Getting old program start")
        old_t = site.live.query_value("GET status\nColumns: program_start\n")

        logger.debug("Read replication changes of site")
        base_dir = site.path("var/check_mk/wato")
        for path in glob.glob(base_dir + "/replication_*"):
            logger.debug("Replication file: %r", path)
            with suppress(FileNotFoundError):
                logger.debug(site.read_file(base_dir + "/" + os.path.basename(path)))

        # Ensure no previous activation is still running
        for status_path in glob.glob(base_dir + "/replication_status_*"):
            logger.debug("Replication status file: %r", status_path)
            with suppress(FileNotFoundError):
                changes = ast.literal_eval(
                    site.read_file(base_dir + "/" + os.path.basename(status_path))
                )
                if changes.get("current_activation") is not None:
                    raise RuntimeError(
                        "A previous activation is still running. Does the wait work?"
                    )

        changed = self.openapi.activate_changes_and_wait_for_completion(
            sites=[site.id], force_foreign_changes=allow_foreign_changes
        )
        if changed:
            logger.info("Waiting for core reloads of: %s", site.id)
            site.wait_for_core_reloaded(old_t)

        self.ensure_running()


def _is_dockerized() -> bool:
    return Path("/.dockerenv").exists()


class SiteFactory:
    def __init__(
        self,
        version: str,
        edition: str,
        branch: str,
        update_from_git: bool = False,
        install_test_python_modules: bool = True,
        prefix: Optional[str] = None,
    ) -> None:
        self._base_ident = prefix or "s_%s_" % branch[:6]
        self._version = version
        self._edition = edition
        self._branch = branch
        self._sites: MutableMapping[str, Site] = {}
        self._index = 1
        self._update_from_git = update_from_git
        self._install_test_python_modules = install_test_python_modules

    @property
    def sites(self) -> Mapping[str, Site]:
        return self._sites

    def get_site(self, name: str) -> Site:
        if "%s%s" % (self._base_ident, name) in self._sites:
            return self._sites["%s%s" % (self._base_ident, name)]
        # For convenience, allow to retreive site by name or full ident
        if name in self._sites:
            return self._sites[name]
        return self._new_site(name)

    def get_existing_site(self, name: str) -> Site:
        if "%s%s" % (self._base_ident, name) in self._sites:
            return self._sites["%s%s" % (self._base_ident, name)]
        # For convenience, allow to retreive site by name or full ident
        if name in self._sites:
            return self._sites[name]
        return self._site_obj(name)

    def remove_site(self, name: str) -> None:
        if "%s%s" % (self._base_ident, name) in self._sites:
            site_id = "%s%s" % (self._base_ident, name)
        elif name in self._sites:
            site_id = name
        else:
            logger.debug("Found no site for name %s.", name)
            return
        logger.info("Removing site %s", site_id)
        self._sites[site_id].rm()
        del self._sites[site_id]

    def _get_ident(self) -> str:
        new_ident = self._base_ident + str(self._index)
        self._index += 1
        return new_ident

    def _site_obj(self, name: str) -> Site:
        site_id = "%s%s" % (self._base_ident, name)
        return Site(
            site_id=site_id,
            reuse=False,
            version=self._version,
            edition=self._edition,
            branch=self._branch,
            update_from_git=self._update_from_git,
            install_test_python_modules=self._install_test_python_modules,
        )

    def _new_site(self, name: str) -> Site:
        site = self._site_obj(name)

        site.create()
        self._sites[site.id] = site

        site.open_livestatus_tcp(encrypted=False)
        site.start()
        site.prepare_for_tests()
        # There seem to be still some changes that want to be activated
        site.activate_changes_and_wait_for_core_reload()
        logger.debug("Created site %s", site.id)
        return site

    def save_results(self) -> None:
        logger.info("Saving results")
        for _site_id, site in sorted(self._sites.items(), key=lambda x: x[0]):
            logger.info("Saving results of site %s", site.id)
            site.save_results()

    def cleanup(self) -> None:
        logger.info("Removing sites")
        for site_id in list(self._sites.keys()):
            self.remove_site(site_id)


def get_site_factory(
    prefix: str, update_from_git: bool, install_test_python_modules: bool
) -> SiteFactory:
    version = os.environ.get("VERSION", CMKVersion.DAILY)
    edition = os.environ.get("EDITION", CMKVersion.CEE)
    branch = os.environ.get("BRANCH")
    if branch is None:
        branch = current_base_branch_name()

    logger.info("Version: %s, Edition: %s, Branch: %s", version, edition, branch)
    return SiteFactory(
        version=version,
        edition=edition,
        branch=branch,
        prefix=prefix,
        update_from_git=update_from_git,
        install_test_python_modules=install_test_python_modules,
    )
