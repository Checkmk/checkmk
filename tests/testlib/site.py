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
import shlex
import shutil
import subprocess
import sys
import time
import urllib.parse
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Final, Literal

import pytest

from tests.testlib.openapi_session import CMKOpenApiSession
from tests.testlib.utils import cmc_path, cme_path, cmk_path, is_containerized
from tests.testlib.version import CMKVersion, version_from_env
from tests.testlib.web_session import CMKWebSession

import livestatus

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)

PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR = sys.version_info.major, sys.version_info.minor


class Site:
    def __init__(
        self,
        version: CMKVersion,
        site_id: str,
        reuse: bool = True,
        update_from_git: bool = False,
        admin_password: str = "cmk",
        update: bool = False,
        update_conflict_mode: str = "install",
        enforce_english_gui: bool = True,
    ) -> None:
        assert site_id
        self.id = site_id
        self.root = "/omd/sites/%s" % self.id
        self.version: Final = version

        self.update_from_git = update_from_git

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
            self._apache_port = int(self.get_config("APACHE_TCP_PORT"))
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
                    f"Config did not update within {timeout} seconds.\nOutput of ps -ef (to check if core is actually running):\n{ps_proc.stdout}"
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
        self, hostname: str, state: int, output: str, expected_state: int | None = None
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
        expected_state: int | None = None,
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
        self, cmd: list[str], *args, preserve_env: list[str] | None = None, **kwargs
    ) -> subprocess.Popen:
        assert isinstance(cmd, list), "The command must be given as list"

        if preserve_env:
            # Skip the test cases calling this for some distros
            # Ubuntu 16.04 does not support --preserve-env nor --whitelist-environment
            # Ubuntu 18.04 does not support --whitelist-environment
            if os.environ.get("DISTRO") in (
                "ubuntu-16.04",
                "ubuntu-18.04",
                "centos-7",
                "centos-8",
                "sles-12sp3",
                "sles-12sp4",
            ):
                pytest.skip("preserve env not possible in this environment")
            sudo_env_args = [f"--preserve-env={','.join(preserve_env)}"]
            su_env_args = ["--whitelist-environment", ",".join(preserve_env)]
        else:
            sudo_env_args = []
            su_env_args = []

        kwargs.setdefault("encoding", "utf-8")
        cmd_txt = " ".join(
            [
                "sudo",
            ]
            + sudo_env_args
            + [
                "su",
                "-l",
                self.id,
            ]
            + su_env_args
            + [
                "-c",
                shlex.quote(" ".join(shlex.quote(p) for p in cmd)),
            ]
        )
        logger.info("Executing: %s", cmd_txt)
        kwargs["shell"] = True
        return subprocess.Popen(cmd_txt, *args, **kwargs)

    def check_output(
        self, cmd: list[str], input: str | None = None  # pylint: disable=redefined-builtin
    ) -> str:
        """Mimics behavior of subprocess.check_output

        Seems to be OK for now but we should find a better abstraction than just
        wrapping self.execute().
        """
        p = self.execute(
            cmd,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if input else None,
        )
        stdout, stderr = p.communicate(input)
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, p.args, stdout, stderr)
        return stdout

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
        cmd = ["sudo", "/usr/bin/omd", mode, self.id] + list(args)
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
        return stdout if stdout is not None else ""

    def read_binary_file(self, rel_path: str) -> bytes:
        p = self.execute(["cat", self.path(rel_path)], stdout=subprocess.PIPE, encoding=None)
        stdout = p.communicate()[0]
        if p.returncode != 0:
            raise Exception("Failed to read file %s. Exit-Code: %d" % (rel_path, p.returncode))
        return stdout

    def delete_file(self, rel_path: str, missing_ok: bool = False) -> None:
        p = self.execute(["rm", "-f", self.path(rel_path)])
        if p.wait() != 0:
            raise Exception("Failed to delete file %s. Exit-Code: %d" % (rel_path, p.wait()))

    def delete_dir(self, rel_path: str) -> None:
        p = self.execute(["rm", "-rf", self.path(rel_path)])
        if p.wait() != 0:
            raise Exception("Failed to delete directory %s. Exit-Code: %d" % (rel_path, p.wait()))

    def _call_tee(self, rel_target_path: str, content: bytes | str) -> None:
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
        self._call_tee(rel_path, content)

    def write_binary_file(self, rel_path: str, content: bytes) -> None:
        self._call_tee(rel_path, content)

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
        p = self.execute(["mkdir", "-p", self.path(rel_path)])
        return p.wait() == 0

    def listdir(self, rel_path: str) -> list[str]:
        p = self.execute(["ls", "-1", self.path(rel_path)], stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        assert p.wait() == 0
        if not output:
            return []
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
            logger.info("Install Checkmk version %s", self.version.version)
            completed_process = subprocess.run(
                [
                    f"{cmk_path()}/scripts/run-pipenv",
                    "run",
                    f"{cmk_path()}/tests/scripts/install-cmk.py",
                ],
                env=dict(os.environ, VERSION=self.version.version),
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
            logger.info("Updating site '%s'" if self.update else "Creating site '%s'", self.id)
            completed_process = subprocess.run(
                [
                    "/usr/bin/sudo",
                    "/usr/bin/omd",
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
                self._enabled_liveproxyd_debug_logging()
            self._enable_mkeventd_debug_logging()
            self._enable_gui_debug_logging()
            self._tune_nagios()

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

    def _update_with_f12_files(self) -> None:
        paths = [
            cmk_path() + "/omd/packages/omd",
            cmk_path() + "/omd/packages/check_mk/skel/etc/init.d",
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
            cmk_path() + "/agent-receiver",
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
                cmc_path() + "/web",
                cmc_path() + "/alert_handlers",
                cmc_path() + "/core",
                # TODO: Do not invoke the chroot build mechanism here, which is very time
                # consuming when not initialized yet
                # cmc_path() + "/agents",
            ]

        if os.path.exists(cme_path()) and self.version.is_managed_edition():
            paths += [
                cme_path(),
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

        assert (
            self.execute(["cmk-update-config"]).wait() == 0
        ), "Failed to execute cmk-update-config"

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

    def _enable_cmc_tooling(self, tool: Literal["helgrind", "memcheck"] | None) -> None:
        if not tool:
            return

        if not os.path.exists("/opt/bin/valgrind"):
            logger.warning("WARNING: /opt/bin/valgrind does not exist. Skip enabling it.")
            return

        self.write_text_file(
            "etc/default/cmc",
            f'CMC_DAEMON_PREPEND="/opt/bin/valgrind --tool={tool} --quiet --log-file=$OMD_ROOT/var/log/cmc-{tool}.log"\n',
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
        completed_process = subprocess.run(
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
        assert completed_process.returncode == 0

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
            stdout = subprocess.check_output(["ps", "-ef"], text=True)
            pytest.exit(
                "Site was not running completely while it should. Enforcing stop. "
                f"Output of ps -ef:\n{stdout}"
            )

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

        if self.enforce_english_gui:
            web = CMKWebSession(self)
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

        user_spec, etag = self.openapi.get_user("cmkadmin")
        user_spec["language"] = "en"
        user_spec.pop("enforce_password_change", None)
        self.openapi.edit_user("cmkadmin", user_spec, etag)

        # Verify the language is as expected now
        r = web.get("user_profile.py", allow_redirect_to_login=True)
        assert "Edit profile" in r.text, "Body: %s" % r.text

    def open_livestatus_tcp(self, encrypted: bool) -> None:
        """This opens a currently free TCP port and remembers it in the object for later use
        Not free of races, but should be sufficient."""
        start_again = False

        if not self.is_stopped():
            start_again = True
            self.stop()

        self.set_config("LIVESTATUS_TCP", "on")
        self._gather_livestatus_port()
        self.set_config("LIVESTATUS_TCP_PORT", str(self._livestatus_port))
        self.set_config("LIVESTATUS_TCP_TLS", "on" if encrypted else "off")

        if start_again:
            self.start()

    def set_livestatus_port_from_config(self) -> None:
        self._livestatus_port = int(self.get_config("LIVESTATUS_TCP_PORT"))

    def _gather_livestatus_port(self) -> None:
        self._livestatus_port = self.get_free_port_from(9123)

    def get_free_port_from(self, port: int) -> int:
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

    def save_results(self) -> None:
        if not is_containerized():
            logger.info("Not containerized: not copying results")
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

    def get_automation_secret(self) -> str:
        secret_path = "var/check_mk/web/automation/automation.secret"
        secret = self.read_file(secret_path).strip()

        if secret == "":
            raise Exception("Failed to read secret from %s" % secret_path)

        return secret

    def activate_changes_and_wait_for_core_reload(
        self, allow_foreign_changes: bool = False, remote_site: Site | None = None
    ) -> None:
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

    def _get_global_flag(self, column: str) -> Literal[1, 0]:
        return self.live.query_value(f"GET status\nColumns: {column}\n") == 1


class SiteFactory:
    def __init__(
        self,
        version: CMKVersion,
        update_from_git: bool = False,
        install_test_python_modules: bool = True,
        prefix: str | None = None,
        update: bool = False,
        update_conflict_mode: str = "install",
        enforce_english_gui: bool = True,
    ) -> None:
        self._version = version
        self._base_ident = prefix or "s_%s_" % version.branch[:6]
        self._sites: MutableMapping[str, Site] = {}
        self._index = 1
        self._update_from_git = update_from_git
        self._update = update
        self._update_conflict_mode = update_conflict_mode
        self._enforce_english_gui = enforce_english_gui

    @property
    def sites(self) -> Mapping[str, Site]:
        return self._sites

    def get_site(self, name: str) -> Site:
        if f"{self._base_ident}{name}" in self._sites:
            return self._sites[f"{self._base_ident}{name}"]
        # For convenience, allow to retrieve site by name or full ident
        if name in self._sites:
            return self._sites[name]
        return self._new_site(name)

    def get_existing_site(self, name: str) -> Site:
        if f"{self._base_ident}{name}" in self._sites:
            return self._sites[f"{self._base_ident}{name}"]
        # For convenience, allow to retrieve site by name or full ident
        if name in self._sites:
            return self._sites[name]
        return self._site_obj(name)

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
        site_id = f"{self._base_ident}{name}"
        return Site(
            version=self._version,
            site_id=site_id,
            reuse=False,
            update_from_git=self._update_from_git,
            update=self._update,
            enforce_english_gui=self._enforce_english_gui,
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
    *,
    prefix: str,
    update_from_git: bool | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> SiteFactory:
    version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        # Note: we cannot specify a fallback branch here by querying git we because we might not be
        # inside a git repository (integration tests run as site user)
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
        update_from_git=version.version_spec == CMKVersion.GIT
        if update_from_git is None
        else update_from_git,
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
    def execute(self) -> Iterator[subprocess.Popen]:
        with self.copy_helper():
            yield self.site.execute(["python3", str(self.site_path)])
