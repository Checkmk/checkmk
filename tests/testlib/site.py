#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import ast
import glob
import inspect
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager, nullcontext, suppress
from pathlib import Path
from pprint import pformat
from typing import Final, Literal

import pytest

from tests.testlib.openapi_session import CMKOpenApiSession
from tests.testlib.utils import (
    check_output,
    cse_openid_oauth_provider,
    current_base_branch_name,
    current_branch_version,
    execute,
    is_containerized,
    makedirs,
    PExpectDialog,
    repo_path,
    restart_httpd,
    ServiceInfo,
    spawn_expect_process,
    wait_until,
    write_file,
)
from tests.testlib.version import CMKVersion, get_min_version, version_from_env, version_gte
from tests.testlib.web_session import CMKWebSession

import livestatus

from cmk.utils.paths import counters_dir, piggyback_dir, piggyback_source_dir
from cmk.utils.version import Edition, Version

logger = logging.getLogger(__name__)

PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR = sys.version_info.major, sys.version_info.minor


class Site:
    def __init__(
        self,
        version: CMKVersion,
        site_id: str,
        reuse: bool = True,
        admin_password: str = "cmk",
        update: bool = False,
        update_conflict_mode: str = "install",
        enforce_english_gui: bool = True,
    ) -> None:
        assert site_id
        self.id = site_id
        self.root = "/omd/sites/%s" % self.id
        self.version: Final = version

        self.reuse = reuse

        self.http_proto = "http"
        self.http_address = "127.0.0.1"
        self._apache_port: int | None = None  # internal cache for the port

        self._livestatus_port: int | None = None
        self.admin_password = admin_password

        self.update = update
        self.update_conflict_mode = update_conflict_mode
        self.enforce_english_gui = enforce_english_gui

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
            self._apache_port = int(self.get_config("APACHE_TCP_PORT", "5000"))
        return self._apache_port

    @property
    def internal_url(self) -> str:
        """This gives the address-port combination where the site-Apache process listens."""
        return f"{self.http_proto}://{self.http_address}:{self.apache_port}/{self.id}/check_mk/"

    @property
    def internal_url_mobile(self) -> str:
        return self.internal_url + "mobile.py"

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
        live = livestatus.SingleSiteConnection(
            "tcp:%s:%d" % (self.http_address, self.livestatus_port)
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
            path = f"/{self.id}/check_mk/{path}"
        return f"{self.http_proto}://{self.http_address}:{self.apache_port}{path}"

    def wait_for_core_reloaded(self, after: float) -> None:
        # Activating changes can involve an asynchronous(!) monitoring
        # core restart/reload, so e.g. querying a Livestatus table immediately
        # might not reflect the changes yet. Ask the core for a successful reload.
        def config_reloaded() -> bool:
            try:
                new_t: int = self.live.query_value("GET status\nColumns: program_start\n")
            except livestatus.MKLivestatusException:
                # Seems like the socket may vanish for a short time. Keep waiting in case
                # of livestatus (connection) issues...
                return False
            return new_t > after

        reload_time, timeout = time.time(), 120
        while not config_reloaded():
            if time.time() > reload_time + timeout:
                ps_proc = subprocess.run(
                    ["ps", "-ef"],
                    capture_output=True,
                    encoding="utf-8",
                    check=True,
                )
                raise Exception(
                    f"Config did not update within {timeout} seconds.\nOutput of ps -ef "
                    f"(to check if core is actually running):\n{ps_proc.stdout}"
                )
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
        self,
        hostname: str,
        state: int,
        output: str,
        expected_state: int | None = None,
        wait_timeout: int = 20,
    ) -> None:
        if expected_state is None:
            expected_state = state
        last_check_before = self._last_host_check(hostname)
        command_timestamp = self._command_timestamp(last_check_before)
        self.live.command(
            f"[{command_timestamp:.0f}] PROCESS_HOST_CHECK_RESULT;{hostname};{state};{output}"
        )
        self._wait_for_next_host_check(
            hostname,
            last_check_before,
            command_timestamp,
            expected_state,
            wait_timeout,
        )

    def send_service_check_result(
        self,
        hostname: str,
        service_description: str,
        state: int,
        output: str,
        expected_state: int | None = None,
        wait_timeout: int = 20,
    ) -> None:
        if expected_state is None:
            expected_state = state
        last_check_before = self._last_service_check(hostname, service_description)
        command_timestamp = self._command_timestamp(last_check_before)
        self.live.command(
            f"[{command_timestamp:.0f}] PROCESS_SERVICE_CHECK_RESULT;{hostname};"
            f"{service_description};{state};{output}"
        )
        self._wait_for_next_service_check(
            hostname,
            service_description,
            last_check_before,
            command_timestamp,
            expected_state,
            wait_timeout,
        )

    def schedule_check(
        self,
        hostname: str,
        service_description: str,
        expected_state: int | None = None,
        wait_timeout: int = 20,
    ) -> None:
        logger.debug("%s;%s schedule check", hostname, service_description)
        last_check_before = self._last_service_check(hostname, service_description)
        logger.debug("%s;%s last check before %r", hostname, service_description, last_check_before)

        command_timestamp = self._command_timestamp(last_check_before)

        command = (
            f"[{command_timestamp:.0f}] SCHEDULE_FORCED_SVC_CHECK;{hostname};"
            f"{service_description};{command_timestamp:.0f}"
        )

        logger.debug("%s;%s: %r", hostname, service_description, command)

        self.live.command(command)

        self._wait_for_next_service_check(
            hostname,
            service_description,
            last_check_before,
            command_timestamp,
            expected_state,
            wait_timeout,
        )

    def reschedule_services(self, hostname: str, max_count: int = 10) -> None:
        """Reschedule services in the test-site for a given host until no pending services are
        found."""
        count = 0
        pending_services = self.get_host_services(hostname, pending=True)

        # reschedule services
        self.schedule_check(hostname, "Check_MK", 0)

        while len(pending_services) > 0 and count < max_count:
            logger.info(
                "The following services in %s host were found with pending status:\n%s.\n"
                "Rescheduling checks...",
                hostname,
                pformat(pending_services),
            )
            self.schedule_check(hostname, "Check_MK", 0)
            pending_services = self.get_host_services(hostname, pending=True)
            count += 1

        assert len(pending_services) == 0

    def get_host_services(self, hostname: str, pending: bool = False) -> dict[str, ServiceInfo]:
        """Return dict for all services in the given site and host.

        If pending=True, return the pending services only.
        """
        services = {}
        for service in self.openapi.get_host_services(
            hostname, columns=["state", "plugin_output"], pending=pending
        ):
            services[service["extensions"]["description"]] = ServiceInfo(
                state=service["extensions"]["state"],
                summary=service["extensions"]["plugin_output"],
            )
        return services

    def set_timezone(self, timezone: str) -> None:
        """Set the timezone of the site."""
        if not timezone:
            return
        restart_site = self.is_running()
        self.stop()
        environment = [
            _
            for _ in self.read_file("etc/environment").splitlines()
            if not _.strip().startswith("TZ=")
        ] + [f"TZ={timezone}"]
        self.write_text_file("etc/environment", "\n".join(environment) + "\n")
        if restart_site:
            self.start()

    @staticmethod
    def _command_timestamp(last_check_before: float) -> float:
        # Ensure the next check result is not in same second as the previous check
        timestamp = time.time()
        while int(last_check_before) == int(timestamp):
            timestamp = time.time()
            time.sleep(0.1)
        return timestamp

    def _wait_for_next_host_check(
        self,
        hostname: str,
        last_check_before: float,
        command_timestamp: float,
        expected_state: int | None = None,
        wait_timeout: int = 20,
    ) -> None:
        query: str = (
            "GET hosts\n"
            "Columns: last_check state plugin_output\n"
            f"Filter: host_name = {hostname}\n"
            f"WaitObject: {hostname}\n"
            f"WaitTimeout: {wait_timeout*1000:d}\n"
            f"WaitTrigger: check\n"
            f"WaitCondition: last_check > {last_check_before:.0f}\n"
        )
        if expected_state is not None:
            query += f"WaitCondition: state = {expected_state}\n"
        last_check, state, plugin_output = self.live.query_row(query)
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
        expected_state: int | None = None,
        wait_timeout: int = 20,
    ) -> None:
        query: str = (
            "GET services\n"
            "Columns: last_check state plugin_output\n"
            f"Filter: host_name = {hostname}\n"
            f"Filter: description = {service_description}\n"
            f"WaitObject: {hostname};{service_description}\n"
            f"WaitTimeout: {wait_timeout*1000:d}\n"
            f"WaitCondition: last_check > {last_check_before:.0f}\n"
            "WaitCondition: has_been_checked = 1\n"
            "WaitTrigger: check\n"
        )
        if expected_state is not None:
            query += f"WaitCondition: state = {expected_state}\n"
        last_check, state, plugin_output = self.live.query_row(query)
        self._verify_next_check_output(
            command_timestamp,
            last_check,
            last_check_before,
            state,
            expected_state,
            plugin_output,
            wait_timeout,
        )

    @staticmethod
    def _verify_next_check_output(
        command_timestamp: float,
        last_check: float,
        last_check_before: float,
        state: int,
        expected_state: int | None,
        plugin_output: str,
        wait_timeout: int = 20,
    ) -> None:
        logger.debug("processing check result took %0.2f seconds", time.time() - command_timestamp)
        if not last_check > last_check_before:
            raise TimeoutError(
                f"Check result not processed within {wait_timeout} seconds "
                f"(last check before reschedule: {last_check_before:.0f}, "
                f"scheduled at: {command_timestamp:.0f}, last check: {last_check:.0f})"
            )
        if expected_state is None:
            return
        assert (
            state == expected_state
        ), f"Expected {expected_state} state, got {state} state, output {plugin_output}"

    def _last_host_check(self, hostname: str) -> float:
        last_check: int = self.live.query_value(
            f"GET hosts\nColumns: last_check\nFilter: host_name = {hostname}\n"
        )
        return last_check

    def _last_service_check(self, hostname: str, service_description: str) -> float:
        last_check: int = self.live.query_value(
            "GET services\n"
            "Columns: last_check\n"
            f"Filter: host_name = {hostname}\n"
            f"Filter: service_description = {service_description}\n"
        )
        return last_check

    def get_host_state(self, hostname: str) -> int:
        state: int = self.live.query_value(
            f"GET hosts\nColumns: state\nFilter: host_name = {hostname}"
        )
        return state

    def execute(  # type: ignore[no-untyped-def]
        self,
        cmd: list[str],
        *args,
        preserve_env: list[str] | None = None,
        **kwargs,
    ) -> subprocess.Popen:
        return execute(
            cmd, *args, preserve_env=preserve_env, sudo=True, substitute_user=self.id, **kwargs
        )

    def check_output(
        self, cmd: list[str], input: str | None = None  # pylint: disable=redefined-builtin
    ) -> str:
        """Mimics subprocess.check_output while running a process as the site user.

        Returns the stdout of the process.
        """
        return check_output(cmd=cmd, input=input, sudo=True, substitute_user=self.id)

    @contextmanager
    def copy_file(self, name: str, target: str) -> Iterator[None]:
        """Copies a file from the same directory as the caller to the site"""
        caller_file = Path(inspect.stack()[2].filename)
        source = caller_file.parent / name
        self.makedirs(os.path.dirname(target))
        self.write_text_file(target, source.read_text())
        try:
            yield
        finally:
            self.delete_file(target)

    def python_helper(self, name: str) -> PythonHelper:
        caller_file = Path(inspect.stack()[1].filename)
        helper_file = caller_file.parent / name
        return PythonHelper(self, helper_file)

    def omd(self, mode: str, *args: str) -> int:
        cmd = ["sudo", "omd", mode, self.id] + list(args)
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
        p = self.execute(["cat", self.path(rel_path)], stdout=subprocess.PIPE)
        stdout = p.communicate()[0]
        if p.returncode != 0:
            raise Exception("Failed to read file %s. Exit-Code: %d" % (rel_path, p.wait()))
        return stdout if isinstance(stdout, str) else ""

    def read_binary_file(self, rel_path: str) -> bytes:
        p = self.execute(["cat", self.path(rel_path)], stdout=subprocess.PIPE, encoding=None)
        stdout = p.communicate()[0]
        if p.returncode != 0:
            raise Exception("Failed to read file %s. Exit-Code: %d" % (rel_path, p.returncode))
        assert isinstance(stdout, bytes)
        return stdout

    def delete_file(self, rel_path: str) -> None:
        p = self.execute(["rm", "-f", self.path(rel_path)])
        if p.wait() != 0:
            raise Exception("Failed to delete file %s. Exit-Code: %d" % (rel_path, p.wait()))

    def delete_dir(self, rel_path: str) -> None:
        p = self.execute(["rm", "-rf", self.path(rel_path)])
        if p.wait() != 0:
            raise Exception("Failed to delete directory %s. Exit-Code: %d" % (rel_path, p.wait()))

    def write_text_file(self, rel_path: str, content: str) -> None:
        write_file(self.path(str(rel_path)), content, sudo=True, substitute_user=self.id)

    def write_binary_file(self, rel_path: str, content: bytes) -> None:
        write_file(self.path(str(rel_path)), content, sudo=True, substitute_user=self.id)

    def create_rel_symlink(self, link_rel_target: str, rel_link_name: str) -> None:
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

    def resolve_path(self, rel_path: Path) -> Path:
        p = self.execute(["readlink", "-e", self.path(str(rel_path))], stdout=subprocess.PIPE)
        if p.wait() != 0:
            raise Exception(f"Failed to read symlink at {rel_path}. Exit-Code: {p.wait()}")
        if p.stdout is None:
            raise Exception(f"Failed to read symlink at {rel_path}. No stdout.")
        return Path(p.stdout.read().strip())

    def file_exists(self, rel_path: str) -> bool:
        p = self.execute(["test", "-e", self.path(rel_path)], stdout=subprocess.PIPE)
        return p.wait() == 0

    def is_file(self, rel_path: str) -> bool:
        return self.execute(["test", "-f", self.path(rel_path)]).wait() == 0

    def is_dir(self, rel_path: str) -> bool:
        return self.execute(["test", "-d", self.path(rel_path)]).wait() == 0

    def file_mode(self, rel_path: str) -> int:
        return int(self.check_output(["stat", "-c", "%f", self.path(rel_path)]).rstrip(), base=16)

    def inode(self, rel_path: str) -> int:
        return int(self.check_output(["stat", "-c", "%i", self.path(rel_path)]).rstrip())

    def makedirs(self, rel_path: str) -> bool:
        return makedirs(self.path(rel_path), sudo=True, substitute_user=self.id)

    def reset_admin_password(self, new_password: str | None = None) -> None:
        self.check_output(
            ["cmk-passwd", "-i", "cmkadmin"], input=new_password or self.admin_password
        )

    def listdir(self, rel_path: str) -> list[str]:
        p = self.execute(["ls", "-1", self.path(rel_path)], stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        assert p.wait() == 0
        if not output:
            return []
        assert isinstance(output, str)
        return output.split("\n")

    def system_temp_dir(self) -> Iterator[str]:
        p = self.execute(
            ["mktemp", "-d", "cmk-system-test-XXXXXXXXX", "-p", "/tmp"], stdout=subprocess.PIPE
        )
        assert p.wait() == 0
        assert p.stdout is not None
        path = p.stdout.read().strip()

        try:
            yield path
        finally:
            p = self.execute(["rm", "-rf", path])
            if p.wait() != 0:
                raise Exception("Failed to delete directory %s. Exit-Code: %d" % (path, p.wait()))

    def cleanup_if_wrong_version(self) -> None:
        if not self.exists():
            return

        if self.current_version_directory() == self.version.version_directory():
            return

        # Now cleanup!
        self.rm()

    def current_version_directory(self) -> str:
        return os.path.split(os.readlink("/omd/sites/%s/version" % self.id))[-1]

    def install_cmk(self) -> None:
        if not self.version.is_installed():
            logger.info("Installing Checkmk version %s", self.version.version_directory())
            completed_process = subprocess.run(
                [
                    f"{repo_path()}/scripts/run-pipenv",
                    "run",
                    f"{repo_path()}/tests/scripts/install-cmk.py",
                ],
                env=dict(
                    os.environ, VERSION=self.version.version, EDITION=self.version.edition.short
                ),
                check=False,
            )
            if completed_process.returncode != 0:
                raise Exception(
                    f"Version {self.version.version} could not be installed! "
                    'Use "tests/scripts/install-cmk.py" or install it manually.'
                )

    def create(self) -> None:
        self.install_cmk()

        if not (self.reuse or self.update) and self.exists():
            raise Exception("The site %s already exists." % self.id)

        if self.update or not self.exists():
            logger.info('Updating site "%s"' if self.update else 'Creating site "%s"', self.id)
            completed_process = subprocess.run(
                [
                    "/usr/bin/sudo",
                    "omd",
                    "-f",
                    "-V",
                    self.version.version_directory(),
                    "update",
                    f"--conflict={self.update_conflict_mode}",
                    self.id,
                ]
                if self.update
                else [
                    "/usr/bin/sudo",
                    "omd",
                    "-V",
                    self.version.version_directory(),
                    "create",
                    "--admin-password",
                    self.admin_password,
                    "--apache-reload",
                    self.id,
                ],
                check=False,
                capture_output=True,
                encoding="utf-8",
            )
            assert not completed_process.returncode, completed_process.stderr
            assert os.path.exists("/omd/sites/%s" % self.id)

            self._ensure_sample_config_is_present()
            # This seems to cause an issue with GUI and XSS crawl (they take too long or seem to
            # hang) job. Disable as a quick fix. We may have to parametrize this per job type.
            # self._set_number_of_apache_processes()
            if not self.version.is_raw_edition():
                self._set_number_of_cmc_helpers()
                self._enable_cmc_core_dumps()
                self._enable_cmc_debug_logging()
                self._enable_cmc_tooling(tool=None)
                self._disable_cmc_log_rotation()
                self._enable_liveproxyd_debug_logging()
            self._enable_mkeventd_debug_logging()
            self._enable_gui_debug_logging()
            self._tune_nagios()

        # The tmpfs is already mounted during "omd create". We have just created some
        # Checkmk configuration files and want to be sure they are used once the core
        # starts.
        self._update_cmk_core_config()

        self.makedirs(self.result_dir())

        self.openapi.port = self.apache_port
        self.openapi.set_authentication_header(
            user="automation", password=self.get_automation_secret()
        )
        # set the sites timezone according to TZ
        self.set_timezone(os.getenv("TZ", ""))

    def _ensure_sample_config_is_present(self) -> None:
        if missing_files := self._missing_but_required_wato_files():
            raise Exception(
                "Sample config was not created by post create hook "
                "01_create-sample-config.py (Missing files: %s)" % missing_files
            )

    def _missing_but_required_wato_files(self) -> list[str]:
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

    def _update_cmk_core_config(self) -> None:
        logger.info("Updating core configuration...")
        p = self.execute(["cmk", "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert p.wait() == 0, "Failed to execute 'cmk -U': %s" % p.communicate()[0]

    def _enable_liveproxyd_debug_logging(self) -> None:
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

    def _enable_cmc_tooling(self, tool: Literal["helgrind", "memcheck"] | None) -> None:
        if not tool:
            return

        if not os.path.exists("/opt/bin/valgrind"):
            logger.warning("WARNING: /opt/bin/valgrind does not exist. Skip enabling it.")
            return

        self.write_text_file(
            "etc/default/cmc",
            f'CMC_DAEMON_PREPEND="/opt/bin/valgrind --tool={tool} --quiet '
            f'--log-file=$OMD_ROOT/var/log/cmc-{tool}.log"\n',
        )

    def _set_number_of_apache_processes(self) -> None:
        self.makedirs("etc/apache/conf.d")
        self.write_text_file(
            "etc/apache/conf.d/tune-server-pool.conf",
            "\n".join(
                [
                    "MinSpareServers 1",
                    "MaxSpareServers 2",
                    "ServerLimit 5",
                    "MaxClients 5",
                ]
            ),
        )

    def _set_number_of_cmc_helpers(self) -> None:
        self.makedirs("etc/check_mk/conf.d")
        self.write_text_file(
            "etc/check_mk/conf.d/cmc-helpers.mk",
            "\n".join(
                [
                    "cmc_check_helpers = 2",
                    "cmc_fetcher_helpers = 2",
                    "cmc_checker_helpers = 2",
                ]
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
                "cmk.web.saml2": 10,
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

    def rm(self, site_id: str | None = None) -> None:
        # Wait a bit to avoid unnecessarily stress testing the site.
        time.sleep(1)
        completed_process = subprocess.run(
            [
                "/usr/bin/sudo",
                "omd",
                "-f",
                "rm",
                "--apache-reload",
                "--kill",
                site_id or self.id,
            ],
            check=False,
        )
        assert completed_process.returncode == 0

    def start(self) -> None:
        if not self.is_running():
            logger.info("Starting site")
            assert self.omd("start") == 0
            # print("= BEGIN PROCESSES AFTER START ==============================")
            # self.execute(["ps", "aux"]).wait()
            # print("= END PROCESSES AFTER START ==============================")
            i = 0
            while not self.is_running():
                i += 1
                if i > 10:
                    self.execute(["omd", "status"]).wait()
                    # print("= BEGIN PROCESSES FAIL ==============================")
                    # self.execute(["ps", "aux"]).wait()
                    # print("= END PROCESSES FAIL ==============================")
                    logger.warning("Could not start site %s. Stop waiting.", self.id)
                    break
                logger.warning("The site %s is not running yet, sleeping... (round %d)", self.id, i)
                sys.stdout.flush()
                time.sleep(0.2)

            self.ensure_running()
        else:
            logger.info("Site is already running")

        assert os.path.ismount(
            self.path("tmp")
        ), "The site does not have a tmpfs mounted! We require this for good performing tests"

    def stop(self) -> None:
        if self.is_stopped():
            return  # Nothing to do
        logger.info("Stopping site")

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
            omd_status_output = self.execute(
                ["omd", "status"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            ).communicate()[0]
            ps_output_file = os.path.join(self.result_dir(), "processes.out")
            self.write_text_file(
                ps_output_file,
                self.execute(
                    ["ps", "-ef"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                ).communicate()[0],
            )
            self.save_results()

            pytest.exit(
                "Site was not running completely while it should be! Enforcing stop.\n\n"
                f"Output of omd status:\n{omd_status_output}\n\n"
                f'See "{ps_output_file}" for full "ps -ef" output!',
            )

    def is_running(self) -> bool:
        return self._omd_status() == 0

    def is_stopped(self) -> bool:
        # 0 -> fully running
        # 1 -> fully stopped
        # 2 -> partially running
        return self._omd_status() == 1

    def _omd_status(self) -> int:
        def _fmt_output(msg: str) -> str:
            return ("\n> " + "\n> ".join(msg.splitlines()) + "\n") if msg else "-"

        try:
            self.check_output(["omd", "status", "--bare"])
            return 0
        except subprocess.CalledProcessError as e:
            logger.info("%s Output: %sSTDERR: %s", e, _fmt_output(e.output), _fmt_output(e.stderr))
            return e.returncode

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

    def get_config(self, key: str, default: str = "") -> str:
        p = self.execute(
            ["omd", "config", "show", key], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        logger.debug("omd config: %s is set to %r", key, stdout.strip())
        if stderr:
            logger.error(stderr)
        return stdout.strip() or default

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
        logger.info("Prepare for tests")
        self.verify_cmk()

        if self.enforce_english_gui:
            web = CMKWebSession(self)
            if not self.version.is_saas_edition():
                web.login()
            self.enforce_non_localized_gui(web)
        self._add_wato_test_config()

    # Add some test configuration that is not test specific. These settings are set only to have a
    # bit more complex Checkmk config.
    def _add_wato_test_config(self) -> None:
        # This entry is interesting because it is a check specific setting. These
        # settings are only registered during check loading. In case one tries to
        # load the config without loading the checks in advance, this leads into an
        # exception.
        # We set this config option here trying to catch this kind of issue.
        self.openapi.create_rule(
            ruleset_name="fileinfo_groups",
            value={"group_patterns": [("TESTGROUP", ("*gwia*", ""))]},
            folder="/",
        )

    def enforce_non_localized_gui(self, web: CMKWebSession) -> None:
        r = web.get("user_profile.py")
        assert "Edit profile" in r.text, "Body: %s" % r.text

        if (user := self.openapi.get_user("cmkadmin")) is None:
            raise Exception("User cmkadmin not found!")
        user_spec, etag = user
        user_spec["language"] = "en"
        user_spec.pop("enforce_password_change", None)
        self.openapi.edit_user("cmkadmin", user_spec, etag)

        # Verify the language is as expected now
        r = web.get("user_profile.py", allow_redirect_to_login=True)
        assert "Edit profile" in r.text, "Body: %s" % r.text

    def open_livestatus_tcp(self, encrypted: bool) -> None:
        """This opens a currently free TCP port and remembers it in the object for later use
        Not free of races, but should be sufficient."""
        # Check if livestatus is already enabled and has correct TLS setting
        if self.get_config("LIVESTATUS_TCP").rstrip() == "on" and (
            self.get_config("LIVESTATUS_TCP_TLS", "off") == ("on" if encrypted else "off")
        ):
            return

        restart_site = self.is_running()
        self.stop()
        self.set_config("LIVESTATUS_TCP", "on")
        self.gather_livestatus_port()
        self.set_config("LIVESTATUS_TCP_PORT", str(self._livestatus_port))
        self.set_config("LIVESTATUS_TCP_TLS", "on" if encrypted else "off")
        if restart_site:
            self.start()

    def gather_livestatus_port(self, from_config: bool = False) -> None:
        if from_config and (config_port := int(self.get_config("LIVESTATUS_TCP_PORT", "0"))):
            self._livestatus_port = config_port
        else:
            self._livestatus_port = self.get_free_port_from(9123)

    @staticmethod
    def get_free_port_from(port: int) -> int:
        used_ports = set()
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

    def toggle_liveproxyd(self, enabled: bool = True) -> None:
        self.set_config("LIVEPROXYD", "on" if enabled else "off", with_restart=True)
        assert self.file_exists("tmp/run/liveproxyd.pid") == enabled

    def save_results(self) -> None:
        if not is_containerized():
            logger.info("Not containerized: not copying results")
            return
        logger.info("Saving to %s", self.result_dir())
        self.makedirs(self.result_dir())

        with suppress(FileNotFoundError):
            shutil.copy(self.path("junit.xml"), self.result_dir())

        shutil.copytree(
            self.path("var/log"),
            "%s/logs" % self.result_dir(),
            ignore_dangling_symlinks=True,
            ignore=shutil.ignore_patterns(".*"),
            dirs_exist_ok=True,
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
                dirs_exist_ok=True,
            )

            # Rename files to get better handling by the browser when opening a crash file
            for crash_info in Path("var/check_mk/crashes").glob("**/crash.info"):
                crash_info.rename(crash_info.parent / (crash_info.stem + ".json"))

    def result_dir(self) -> str:
        return os.path.join(os.environ.get("RESULT_PATH", self.path("results")), self.id)

    def get_automation_secret(self) -> str:
        secret_path = "var/check_mk/web/automation/automation.secret"
        secret = self.read_file(secret_path).strip()

        if secret == "":
            raise Exception("Failed to read secret from %s" % secret_path)

        return secret

    def get_site_internal_secret(self) -> bytes:
        secret_path = "etc/site_internal.secret"
        secret = self.read_binary_file(secret_path)

        if secret == b"":
            raise Exception("Failed to read secret from %s" % secret_path)

        return secret

    def activate_changes_and_wait_for_core_reload(
        self, allow_foreign_changes: bool = False, remote_site: Site | None = None
    ) -> None:
        logger.info("Activate changes and wait for reload...")
        self.ensure_running()
        try:
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
        finally:
            self.ensure_running()

    def is_global_flag_enabled(self, column: str) -> bool:
        return self._get_global_flag(column) == 1

    def is_global_flag_disabled(self, column: str) -> bool:
        return self._get_global_flag(column) == 0

    def _get_global_flag(self, column: str) -> bool:
        return bool(self.live.query_value(f"GET status\nColumns: {column}\n") == 1)

    def stop_host_checks(self) -> None:
        logger.info("Stopping execution of host-checks...")
        self.live.command("STOP_EXECUTING_HOST_CHECKS")
        wait_until(
            lambda: self.is_global_flag_disabled("execute_host_checks"), timeout=60, interval=1
        )

    def start_host_checks(self) -> None:
        logger.info("Starting execution of host-checks...")
        self.live.command("START_EXECUTING_HOST_CHECKS")
        wait_until(
            lambda: self.is_global_flag_enabled("execute_host_checks"), timeout=60, interval=1
        )

    def stop_active_services(self) -> None:
        logger.info("Stopping execution of active services...")
        self.live.command("STOP_EXECUTING_SVC_CHECKS")
        wait_until(
            lambda: self.is_global_flag_disabled("execute_service_checks"), timeout=60, interval=1
        )

    def start_active_services(self) -> None:
        logger.info("Starting execution of active services...")
        self.live.command("START_EXECUTING_SVC_CHECKS")
        wait_until(
            lambda: self.is_global_flag_enabled("execute_service_checks"), timeout=60, interval=1
        )


class SiteFactory:
    def __init__(
        self,
        version: CMKVersion,
        prefix: str | None = None,
        update: bool = False,
        update_conflict_mode: str = "install",
        enforce_english_gui: bool = True,
    ) -> None:
        self.version = version
        self._base_ident = prefix if prefix is not None else "s_%s_" % version.branch[:6]
        self._sites: MutableMapping[str, Site] = {}
        self._index = 1
        self._update = update
        self._update_conflict_mode = update_conflict_mode
        self._enforce_english_gui = enforce_english_gui

    @property
    def sites(self) -> Mapping[str, Site]:
        return self._sites

    def get_site(
        self,
        name: str,
        start: bool = True,
        init_livestatus: bool = True,
        prepare_for_tests: bool = True,
        activate_changes: bool = True,
    ) -> Site:
        site = self._site_obj(name)

        site.create()

        if init_livestatus:
            site.open_livestatus_tcp(encrypted=False)

        if not start:
            return site

        site.start()

        if prepare_for_tests:
            site.prepare_for_tests()

        if activate_changes:
            # There seem to be still some changes that want to be activated
            site.activate_changes_and_wait_for_core_reload()

        logger.debug("Created site %s", site.id)
        return site

    def get_existing_site(
        self,
        name: str,
        start: bool = True,
        init_livestatus: bool = True,
    ) -> Site:
        site = self._site_obj(name)

        if site.exists() and init_livestatus:
            site.gather_livestatus_port(from_config=True)

        if not (site.exists() and start):
            return site

        site.start()

        logger.debug("Reused site %s", site.id)
        return site

    def restore_site_from_backup(self, backup_path: Path, name: str, reuse: bool = False) -> Site:
        self._base_ident = ""
        site = self._site_obj(name)

        if not reuse:
            assert (
                not site.exists()
            ), f"Site {name} already existing. Please remove it before restoring it from a backup."

        site.install_cmk()
        logger.info("Creating %s site from backup...", name)

        omd_restore_cmd = (
            ["sudo", "omd", "restore"] + (["--reuse", "--kill"] if reuse else []) + [backup_path]
        )

        completed_process = subprocess.run(
            omd_restore_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )

        assert completed_process.returncode == 0

        site = self.get_existing_site(site.id)
        site.start()
        restart_httpd()

        return site

    def interactive_create(self, name: str, logfile_path: str = "/tmp/omd_install.out") -> Site:
        """Interactive site creation via Pexpect"""
        self._base_ident = ""
        site = self._site_obj(name)
        site.install_cmk()

        rc = spawn_expect_process(
            [
                "/usr/bin/sudo",
                "omd",
                "-V",
                self.version.version_directory(),
                "create",
                "--admin-password",
                site.admin_password,
                "--apache-reload",
                name,
            ],
            dialogs=[],
            logfile_path=logfile_path,
        )

        assert rc == 0, f"Executed command returned {rc} exit status. Expected: 0"

        with open(logfile_path) as logfile:
            logger.debug("OMD automation logfile: %s", logfile.read())

        # refresh the site object after creating the site
        site = self.get_existing_site(site.id)

        # open the livestatus port
        site.open_livestatus_tcp(encrypted=False)

        # start the site after manually installing it
        site.start()

        assert site.is_running(), "Site is not running!"
        logger.info("Test-site %s is up", site.id)

        restart_httpd()

        return site

    def interactive_update(
        self,
        test_site: Site,
        target_version: CMKVersion,
        min_version: CMKVersion,
        conflict_mode: str = "keepold",
        logfile_path: str = "/tmp/sep.out",
    ) -> Site:
        """Update the test-site with the given target-version, if supported.

        Such update process is performed interactively via Pexpect.
        """
        self.version = target_version
        site = self.get_existing_site(test_site.id)
        site.install_cmk()
        site.stop()

        logger.info(
            "Updating %s site from %s version to %s version...",
            test_site.id,
            test_site.version.version,
            target_version.version_directory(),
        )

        pexpect_dialogs = []
        version_supported = self._version_supported(test_site.version.version, min_version.version)
        if version_supported:
            logger.info("Updating to a supported version.")
            pexpect_dialogs.extend(
                [
                    PExpectDialog(
                        expect=(
                            f"You are going to update the site {test_site.id} "
                            f"from version {test_site.version.version_directory()} "
                            f"to version {target_version.version_directory()}."
                        ),
                        send="u\r",
                    )
                ]
            )
        else:  # update-process not supported. Still, verify the correct message is displayed
            logger.info(
                "Updating from version %s to version %s is not supported",
                min_version,
                target_version,
            )

            pexpect_dialogs.extend(
                [
                    PExpectDialog(
                        expect=(
                            f"ERROR: You are trying to update from "
                            f"{test_site.version.version_directory()} to "
                            f"{target_version.version_directory()} which is not supported."
                        ),
                        send="\r",
                    )
                ]
            )

        pexpect_dialogs.extend(
            [PExpectDialog(expect="Wrong permission", send="d", count=0, optional=True)]
        )

        rc = spawn_expect_process(
            [
                "/usr/bin/sudo",
                "omd",
                "-V",
                target_version.version_directory(),
                "update",
                f"--conflict={conflict_mode}",
                test_site.id,
            ],
            dialogs=pexpect_dialogs,
            logfile_path=logfile_path,
        )
        if version_supported:
            assert rc == 0, f"Executed command returned {rc} exit status. Expected: 0"
        else:
            assert rc == 256, f"Executed command returned {rc} exit status. Expected: 256"
            pytest.skip(f"{test_site.version} is not a supported version for {target_version}")

        with open(logfile_path) as logfile:
            logger.debug("OMD automation logfile: %s", logfile.read())

        # refresh the site object after creating the site
        self._base_ident = ""
        site = self.get_existing_site(test_site.id)

        # restoring the tmpfs was broken and has been fixed with
        # 3448a7da56ed6d4fa2c2f425d0b1f4b6e02230aa
        from_version = Version.from_str(test_site.version.version)
        if (
            (Version.from_str("2.1.0p36") <= from_version < Version.from_str("2.2.0"))
            or (Version.from_str("2.2.0p13") <= from_version < Version.from_str("2.3.0"))
            or Version.from_str("2.3.0b1") <= from_version
        ):
            # tmpfs should have been restored:
            assert os.path.exists(site.path(counters_dir))
            assert os.path.exists(site.path(str(piggyback_dir)))
            assert os.path.exists(site.path(str(piggyback_source_dir)))

        # open the livestatus port
        site.open_livestatus_tcp(encrypted=False)

        # start the site after manually installing it
        site.start()

        assert site.is_running(), "Site is not running!"
        logger.info("Site %s is up", site.id)

        restart_httpd()

        assert site.version.version == target_version.version, "Version mismatch during update!"
        assert (
            site.version.edition.short == target_version.edition.short
        ), "Edition mismatch during update!"

        return site

    def update_as_site_user(
        self,
        test_site: Site,
        target_version: CMKVersion = version_from_env(
            fallback_version_spec=CMKVersion.DAILY,
            fallback_edition=Edition.CEE,
            fallback_branch=current_base_branch_name(),
        ),
        min_version: CMKVersion = CMKVersion(
            get_min_version(),
            Edition.CEE,
            current_base_branch_name(),
            current_branch_version(),
        ),
        conflict_mode: str = "keepold",
    ) -> Site:
        version_supported = self._version_supported(test_site.version.version, min_version.version)
        if not version_supported:
            pytest.skip(
                f"{test_site.version} is not a supported version for {target_version.version}"
            )
        self.version = target_version
        site = self.get_existing_site("central", init_livestatus=False)
        site.install_cmk()
        site.stop()

        logger.info(
            "Updating %s site from %s version to %s version...",
            test_site.id,
            test_site.version.version,
            target_version.version_directory(),
        )

        cmd = [
            "omd",
            "-f",
            "-V",
            target_version.version_directory(),
            "update",
            f"--conflict={conflict_mode}",
        ]
        test_site.stop()
        process = test_site.execute(cmd)
        rc = process.wait()
        assert rc == 0, process.stderr

        # refresh the site object after creating the site
        site = self.get_existing_site("central")
        # open the livestatus port
        site.open_livestatus_tcp(encrypted=False)
        # start the site after manually installing it
        site.start()

        assert site.is_running(), "Site is not running!"
        logger.info("Site %s is up", site.id)

        restart_httpd()

        assert site.version.version == target_version.version, "Version mismatch during update!"
        assert (
            site.version.edition.short == target_version.edition.short
        ), "Edition mismatch during update!"

        site.openapi.activate_changes_and_wait_for_completion()

        return test_site

    @staticmethod
    def _version_supported(version: str, min_version: str) -> bool:
        """Check if the given version is supported for updating."""
        return version_gte(version, min_version)

    def get_test_site(
        self,
        name: str = "central",
        description: str = "",
        auto_cleanup: bool = True,
        auto_restart_httpd: bool = False,
        init_livestatus: bool = True,
        save_results: bool = True,
    ) -> Iterator[Site]:
        """Return a fully set-up test site (for use in site fixtures)."""
        reuse_site = os.environ.get("REUSE", "0") == "1"
        # by default, the site will be cleaned up if REUSE=1 is not set
        # you can also explicitly set CLEANUP=[0|1] though (for debug purposes)
        cleanup_site = (
            not reuse_site
            if os.environ.get("CLEANUP") is None
            else os.environ.get("CLEANUP") == "1"
        )
        site = self.get_existing_site(name, start=reuse_site)
        if site.exists():
            if reuse_site:
                logger.info('Reusing existing site "%s" (REUSE=1)', site.id)
            else:
                logger.info('Dropping existing site "%s" (REUSE=0)', site.id)
                site.rm()
        if not site.exists():
            site = self.get_site(
                name,
                init_livestatus=init_livestatus,
                prepare_for_tests=not self.version.is_saas_edition(),
            )
        site.start()
        if auto_restart_httpd:
            restart_httpd()
        logger.info(
            'Site "%s" is ready!%s',
            site.id,
            f" [{description}]" if description else "",
        )
        with cse_openid_oauth_provider(
            f"http://localhost:{site.apache_port}"
        ) if self.version.is_saas_edition() else nullcontext():
            if self.version.is_saas_edition():
                site.prepare_for_tests()
                site.activate_changes_and_wait_for_core_reload()
            try:
                yield site
            finally:
                # teardown: saving results and removing site
                if save_results:
                    site.save_results()
                if auto_cleanup and cleanup_site:
                    logger.info('Dropping site "%s" (CLEANUP=1)', site.id)
                    site.rm()

    def remove_site(self, name: str) -> None:
        if f"{self._base_ident}{name}" in self._sites:
            site_id = f"{self._base_ident}{name}"
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
        if f"{self._base_ident}{name}" in self._sites:
            return self._sites[f"{self._base_ident}{name}"]
        # For convenience, allow to retrieve site by name or full ident
        if name in self._sites:
            return self._sites[name]

        site_id = f"{self._base_ident}{name}"

        return Site(
            version=self.version,
            site_id=site_id,
            reuse=False,
            update=self._update,
            enforce_english_gui=self._enforce_english_gui,
        )

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
    *,
    prefix: str,
    version: CMKVersion | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> SiteFactory:
    version = version or version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=fallback_branch,
    )
    logger.info(
        "Version: %s, Edition: %s, Branch: %s",
        version.version,
        version.edition.long,
        version.branch,
    )
    return SiteFactory(
        version=version,
        prefix=prefix,
    )


class PythonHelper:
    """Execute a python helper script executed in the site context

    Several tests need to execute some python code in the context
    of the Checkmk site under test. This object helps to copy
    and execute the script."""

    def __init__(self, site: Site, helper_path: Path) -> None:
        self.site: Final = site
        self.helper_path: Final = helper_path
        self.site_path: Final = Path(site.root, self.helper_path.name)

    @contextmanager
    def copy_helper(self) -> Iterator[None]:
        self.site.write_text_file(
            str(self.site_path.relative_to(self.site.root)),
            self.helper_path.read_text(),
        )
        try:
            yield
        finally:
            self.site.delete_file(str(self.site_path))

    def check_output(self, input: str | None = None) -> str:  # pylint: disable=redefined-builtin
        with self.copy_helper():
            return self.site.check_output(["python3", str(self.site_path)], input)

    @contextmanager
    def execute(self, *args, **kwargs) -> Iterator[subprocess.Popen]:  # type: ignore[no-untyped-def]
        with self.copy_helper():
            yield self.site.execute(["python3", str(self.site_path)], *args, **kwargs)
