#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Module for managing Checkmk test sites.

This module provides classes and functions for managing Checkmk test sites. The main classes are
    - Site:
        encapsulates operations for managing a Checkmk site within a test environment.
    - SiteFactory`:
        provides a factory for creating and managing (including teardown of) Checkmk
        test sites.
    - PythonHelper:
        provides a helper for running Python scripts within a Checkmk test site.
"""

from __future__ import annotations

import ast
import glob
import inspect
import json
import logging
import os
import pprint
import re
import subprocess
import sys
import time
import urllib.parse
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext, suppress
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from typing import Any, Final, Literal, overload

import pytest
import pytest_check

import livestatus

from cmk import trace
from cmk.crypto.certificate import Certificate
from cmk.crypto.password import Password
from cmk.crypto.secrets import Secret
from tests.testlib.common.repo import current_branch_name, repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.nonfree.cloud.utils import (  # type: ignore[import-untyped, unused-ignore]
    create_cse_initial_config,
    cse_openid_oauth_provider,
)
from tests.testlib.openapi_session import AgentReceiverApiSession, CMKOpenApiSession
from tests.testlib.utils import (
    check_output,
    execute,
    get_processes_by_cmdline,
    is_cleanup_enabled,
    is_containerized,
    makedirs,
    PExpectDialog,
    read_file,
    restart_httpd,
    run,
    ServiceInfo,
    spawn_expect_process,
    write_file,
)
from tests.testlib.version import (
    CMKPackageInfo,
    CMKPackageInfoOld,
    CMKVersion,
    edition_from_env,
    get_min_version,
    TypeCMKEdition,
    TypeCMKEditionOld,
    version_from_env,
)
from tests.testlib.web_session import CMKWebSession

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()

ADMIN_USER: Final[str] = "cmkadmin"
AUTOMATION_USER: Final[str] = "not_automation"
PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR = sys.version_info.major, sys.version_info.minor


@dataclass
class TracingConfig:
    collect_traces: bool
    otlp_endpoint: str
    extra_resource_attributes: Mapping[str, str]


NO_TRACING = TracingConfig(collect_traces=False, otlp_endpoint="", extra_resource_attributes={})


class Site:
    """
    Represents a Checkmk site for test and development environments.

    This class encapsulates the operations and configurations necessary to manage a Checkmk site,
    including installation, lifecycle management, command execution, and file operations.
    It provides high-level methods to restart core services, schedule checks, query the site status,
    and manipulate site-related files and configurations.
    """

    def __init__(
        self,
        package: CMKPackageInfo | CMKPackageInfoOld,
        site_id: str,
        reuse: bool = True,
        admin_password: str = "cmk",
        enforce_english_gui: bool = True,
        check_wait_timeout: int = 20,
    ) -> None:
        assert site_id
        self.id = site_id
        self.root = Path("/omd/sites") / self.id
        self._package = package
        # keep track of the initial installation status to be able to
        # uninstall only if the version was not installed already
        self._package_was_preinstalled = self._package.is_installed()

        self.reuse = reuse

        self.http_proto = "http"
        self.http_address = "127.0.0.1"
        self._apache_port: int | None = None  # internal cache for the port
        self._message_broker_port: int | None = None

        self._livestatus_port: int | None = None
        self.admin_password = admin_password
        self._automation_secret: Password | None = None

        self.enforce_english_gui = enforce_english_gui

        self.check_wait_timeout = check_wait_timeout

        # We start with ADMIN_USER and change it to the automation user once it is created
        self.openapi = CMKOpenApiSession(
            host=self.http_address,
            port=self.apache_port if self.exists() else 80,
            user=ADMIN_USER,
            password=self.admin_password,
            site=self.id,
            site_version=self._package.version,
        )
        self.openapi_agent_receiver = AgentReceiverApiSession(
            openapi_session=self.openapi,
        )

        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.known_crashes: set[Path] = set()

    @property
    def alias(self) -> str:
        return self.id.replace("_", " ").capitalize()

    @property
    def version(self) -> CMKVersion:
        return self._package.version

    @property
    def edition(self) -> TypeCMKEdition | TypeCMKEditionOld:
        return self._package.edition

    @property
    def package(self) -> CMKPackageInfo | CMKPackageInfoOld:
        return self._package

    @property
    def apache_port(self) -> int:
        if self._apache_port is None:
            self._apache_port = int(self.get_config("APACHE_TCP_PORT", "5000"))
        return self._apache_port

    @property
    def url_prefix(self) -> str:
        """This gives the prefix for the URL of the site."""
        return f"{self.http_proto}://{self.http_address}:{self.apache_port}/{self.id}/"

    @property
    def internal_url(self) -> str:
        """This gives the address-port combination where the site-Apache process listens."""
        return self.url_prefix + "check_mk/"

    @property
    def internal_url_mobile(self) -> str:
        return self.internal_url + "mobile.py"

    @property
    def licensing_dir(self) -> Path:
        return self.root / "var" / "check_mk" / "licensing"

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

    @property
    def message_broker_port(self) -> int:
        if self._message_broker_port is None:
            self._message_broker_port = int(self.get_config("RABBITMQ_PORT", "5672"))
        return self._message_broker_port

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

    @tracer.instrument("Site.restart_core")
    def restart_core(self) -> None:
        # Remember the time for the core reload check and wait a second because the program_start
        # is reported as integer and wait_for_core_reloaded() compares with ">".
        before_restart = time.time()
        time.sleep(1)
        self.omd("restart", "core")
        self.wait_for_core_reloaded(before_restart)

    @tracer.instrument("Site.send_host_check_result")
    def send_host_check_result(
        self,
        hostname: str,
        state: int,
        output: str,
        expected_state: int | None = None,
        wait_timeout: int | None = None,
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

    @tracer.instrument("Site.send_service_check_result")
    def send_service_check_result(
        self,
        hostname: str,
        service_description: str,
        state: int,
        output: str,
        expected_state: int | None = None,
        wait_timeout: int | None = None,
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

    @tracer.instrument("Site.schedule_check")
    def schedule_check(
        self,
        hostname: str,
        service_description: str,
        expected_state: int | None = None,
        wait_timeout: int | None = None,
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

    @tracer.instrument("Site.reschedule_services")
    def reschedule_services(
        self,
        hostname: str,
        max_count: int = 10,
        strict: bool = True,
        wait_timeout: int | None = None,
    ) -> None:
        """Reschedule services in the test-site for a given host until no pending services are
        found.

        Args:
            hostname: Name of the target host.
            max_count: Maximum number of iterations.
            strict: Assert having no pending services.
            wait_timeout: Number of seconds to wait for the service check.
        """
        count = 0
        while (
            len(pending_services := self.get_host_services(hostname, pending=True)) > 0
            and count < max_count
        ):
            logger.info(
                "The following services in %s host are in pending state:\n%s\n"
                "Rescheduling checks...",
                hostname,
                pformat(pending_services),
            )
            self.schedule_check(hostname, "Check_MK", 0, wait_timeout)
            count += 1

        if strict:
            assert len(pending_services) == 0, (
                "The following services are in pending state after rescheduling checks:"
                f"\n{pformat(pending_services)}\n"
            )
        if pending_services:
            logger.info(
                '%s pending service(s) found on host "%s": %s',
                len(pending_services),
                hostname,
                ",".join(list(pending_services.keys())),
            )

    def is_service_in_expected_state_after_rescheduling(
        self, host_name: str, service_name: str, expected_state: int
    ) -> bool:
        """Reschedule the 'Check_MK' and check if the service reaches the expected state."""
        self.schedule_check(host_name, "Check_MK", 0, 5)
        actual_service_state: int = self.live.query_value(
            f"GET services\nColumns: state\nFilter: host_name = {host_name}\n"
            f"Filter: service_description = {service_name}\n"
        )
        return actual_service_state == expected_state

    @tracer.instrument("Site.wait_for_service_state_update")
    def wait_for_services_state_update(
        self,
        hostname: str,
        service_description: str,
        expected_state: int,
        wait_timeout: int,
        max_count: int = 10,
    ) -> None:
        """Wait for the update of the provided service util no pending services are found"""
        count = 0
        while (
            len(pending_services := self.get_host_services(hostname, pending=True)) > 0
            and count < max_count
        ):
            logger.info(
                "The following services in %s host are in pending state:\n%s\n"
                "Waiting for the next update...",
                hostname,
                pformat(pending_services),
            )
            last_check_before = self._last_service_check(hostname, service_description)
            logger.debug(
                "%s;%s last check before %r", hostname, service_description, last_check_before
            )

            command_timestamp = self._command_timestamp(last_check_before)
            self._wait_for_next_service_check(
                hostname,
                service_description,
                last_check_before,
                command_timestamp,
                expected_state,
                wait_timeout,
            )
            count += 1

        assert len(pending_services) == 0, (
            "The following services are in pending state after waiting:"
            f"\n{pformat(pending_services)}\n"
        )

    def get_host_services(
        self,
        hostname: str,
        pending: bool | None = None,
        extra_columns: Sequence[str] = (),
    ) -> dict[str, ServiceInfo]:
        """Return dict for all services in the given site and host.

        If pending=True, return the pending services only.
        """
        services = {}

        mandatory_columns = ["state", "plugin_output"]

        columns = mandatory_columns + [
            column for column in extra_columns if column not in mandatory_columns
        ]

        for service in self.openapi.services.get_host_services(
            hostname, columns=columns, pending=pending
        ):
            services[service["extensions"]["description"]] = ServiceInfo(
                state=service["extensions"]["state"],
                summary=service["extensions"]["plugin_output"],
                extra_columns={
                    column: service["extensions"][column]
                    for column in extra_columns
                    if column in service["extensions"]
                },
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
        self.write_file("etc/environment", "\n".join(environment) + "\n")
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
        wait_timeout: int | None = None,
    ) -> None:
        query: str = (
            "GET hosts\n"
            "Columns: last_check state plugin_output\n"
            f"Filter: host_name = {hostname}\n"
            f"WaitObject: {hostname}\n"
            f"WaitTimeout: {(wait_timeout or self.check_wait_timeout) * 1000:d}\n"
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
        wait_timeout: int | None = None,
    ) -> None:
        query: str = (
            "GET services\n"
            "Columns: last_check state plugin_output\n"
            f"Filter: host_name = {hostname}\n"
            f"Filter: description = {service_description}\n"
            f"WaitObject: {hostname};{service_description}\n"
            f"WaitTimeout: {(wait_timeout or self.check_wait_timeout) * 1000:d}\n"
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

    def _verify_next_check_output(
        self,
        command_timestamp: float,
        last_check: float,
        last_check_before: float,
        state: int,
        expected_state: int | None,
        plugin_output: str,
        wait_timeout: int | None = None,
    ) -> None:
        logger.debug("processing check result took %0.2f seconds", time.time() - command_timestamp)
        if not last_check > last_check_before:
            raise TimeoutError(
                f"Check result not processed within {wait_timeout or self.check_wait_timeout} seconds "
                f"(last check before reschedule: {last_check_before:.0f}, "
                f"scheduled at: {command_timestamp:.0f}, last check: {last_check:.0f})"
            )
        if expected_state is None:
            return
        assert state == expected_state, (
            f"Expected {expected_state} state, got {state} state, output {plugin_output}"
        )

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

    def wait_until_service_has_been_checked(
        self, hostname: str, service_name: str, timeout: int = 10
    ) -> None:
        """Wait until the given service has been executed for a given host.

        Args:
            hostname: The hostname to check.
            service_name: The name of the service to check.
            timeout: The maximum time to wait for the service to be executed (in seconds).

        Raises:
            TimeoutError: If the service has not been executed within the timeout.
        """

        def _has_ping_been_executed() -> bool:
            """Check if the PING service has been executed."""
            host_services = self.get_host_services(hostname, extra_columns=("has_been_checked",))
            return bool(host_services[service_name].extra_columns["has_been_checked"] == 1)

        wait_until(_has_ping_been_executed, timeout=timeout, interval=0.5)

    def get_host_state(self, hostname: str) -> int:
        state: int = self.live.query_value(
            f"GET hosts\nColumns: state\nFilter: host_name = {hostname}"
        )
        return state

    def execute(
        self,
        cmd: list[str],
        preserve_env: list[str] | None = None,
        **kwargs: Any,
    ) -> subprocess.Popen[str]:
        return execute(cmd, preserve_env=preserve_env, sudo=True, substitute_user=self.id, **kwargs)

    def run(
        self,
        args: list[str],
        capture_output: bool = True,
        check: bool = True,
        encoding: str | None = "utf-8",
        input_: str | None = None,
        preserve_env: list[str] | None = None,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        return run(
            args=args,
            capture_output=capture_output,
            check=check,
            input_=input_,
            encoding=encoding,
            preserve_env=preserve_env,
            sudo=True,
            substitute_user=self.id,
            **kwargs,
        )

    @overload
    def check_output(
        self,
        cmd: list[str],
        encoding: str = "utf-8",
        input_: str | None = None,
        preserve_env: list[str] | None = None,
        **kwargs: Any,
    ) -> str: ...

    @overload
    def check_output(
        self,
        cmd: list[str],
        encoding: None,
        input_: str | None = None,
        preserve_env: list[str] | None = None,
        **kwargs: Any,
    ) -> bytes: ...

    def check_output(
        self,
        cmd: list[str],
        encoding: str | None = "utf-8",
        input_: str | None = None,
        preserve_env: list[str] | None = None,
        **kwargs: Any,
    ) -> str | bytes:
        """Mimics subprocess.check_output while running a process as the site user.

        Returns the stdout of the process.
        """
        output = check_output(
            cmd=cmd,
            input_=input_,
            encoding=encoding,
            preserve_env=preserve_env,
            sudo=True,
            substitute_user=self.id,
            **kwargs,
        )
        return output

    @contextmanager
    def copy_file(self, source_path: str | Path, target_path: str | Path) -> Iterator[Path]:
        """Copies a file from the same directory as the caller to the site.

        If absolute paths are passed, those will override the default source and target paths.

        Args:
            source_path: Source path of the file (either absolute or relative to the callers folder).
            target_path: Target path of the file (either absolute or relative to the site).
        """
        caller_file = Path(inspect.stack()[2].filename)
        source_path = caller_file.parent / source_path
        target_path = self.path(target_path)
        self.makedirs(target_path.parent)
        self.write_file(target_path, source_path.read_text())
        try:
            yield target_path
        finally:
            self.delete_file(target_path)

    def python_helper(self, name: str) -> PythonHelper:
        caller_file = Path(inspect.stack()[1].filename)
        helper_file = caller_file.parent / name
        return PythonHelper(self, helper_file)

    def omd(self, mode: str, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        """run the "omd" command with the given mode and arguments.

        Args:
            mode (str): The mode of the "omd" command. e.g. "status", "restart", "start", "stop", "reload"
            args (str): More (optional) arguments to the "omd" command.
            check (bool, optional): Run cmd as check/strict - raise Exception on rc!=0.

        raises:
            subprocess.CalledProcessError: If check is True and the return code is not 0.
                Will also contain the output of the command in the exception message.

        Returns:
            CompletedProcess: the process object resulted from the "omd" command
        """
        cmd = ["omd", mode] + list(args)
        logger.info("Executing: %s", subprocess.list2cmdline(cmd))
        completed_process = self.run(cmd, check=check)
        logger.info("Exit code: %d", completed_process.returncode)
        if completed_process.stdout:
            logger.debug("Stdout:")
            for line in completed_process.stdout.strip().split("\n"):
                logger.debug("> %s", line)
        if completed_process.stderr:
            logger.info("Stderr:")
            for line in completed_process.stderr.strip().split("\n"):
                logger.info("> %s", line)

        if mode == "status":
            logger.info(
                "OMD status: %d (%s)",
                completed_process.returncode,
                {
                    0: "fully running",
                    1: "fully stopped",
                    2: "partially running",
                }.get(completed_process.returncode, "unknown meaning"),
            )

        return completed_process

    def path(self, rel_path: str | Path) -> Path:
        return self.root / rel_path

    def file_mtime(self, rel_path: str | Path) -> float:
        """Return the last modification time of a file."""
        try:
            stdout = self.check_output(["stat", "-c", "%Y", self.path(rel_path).as_posix()])
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to read file '{rel_path}'!")
            raise excp
        return float(stdout)

    @overload
    def read_file(
        self,
        rel_path: str | Path,
        encoding: str = "utf-8",
    ) -> str: ...

    @overload
    def read_file(
        self,
        rel_path: str | Path,
        encoding: None,
    ) -> bytes: ...

    def read_file(
        self,
        rel_path: str | Path,
        encoding: str | None = "utf-8",
    ) -> str | bytes:
        """Read a file as the site user."""
        return read_file(self.path(rel_path), encoding=encoding, sudo=True, substitute_user=self.id)

    def delete_file(self, rel_path: str | Path) -> None:
        try:
            _ = self.run(["rm", "-f", self.path(rel_path).as_posix()])
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to read file '{rel_path}'!")
            raise excp

    def move_file(self, src_rel_path: str | Path, dst_rel_path: str | Path) -> None:
        """Move a file from one path to another within the site.

        Note - directories mentioned within `dst_rel_path` must exist for successful operation!
        """
        try:
            _ = self.run(
                ["mv", self.path(src_rel_path).as_posix(), self.path(dst_rel_path).as_posix()]
            )
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to move file from '{src_rel_path}' to '{dst_rel_path}'!")
            raise excp

    def delete_dir(self, rel_path: str | Path) -> None:
        try:
            _ = self.run(["rm", "-rf", self.path(rel_path).as_posix()])
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to delete directory '{rel_path}'!")
            raise excp

    def write_file(
        self,
        rel_path: str | Path,
        content: bytes | str,
    ) -> None:
        """Write a file as the site user."""
        write_file(self.path(rel_path), content, sudo=True, substitute_user=self.id)

    def create_rel_symlink(self, link_rel_target: str | Path, rel_link_name: str) -> None:
        try:
            _ = self.run(["ln", "-s", Path(link_rel_target).as_posix(), rel_link_name])
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to create symlink from {rel_link_name} to ./{link_rel_target}!")
            raise excp

    def resolve_path(self, rel_path: str | Path) -> Path:
        try:
            stdout = self.check_output(["readlink", "-e", self.path(rel_path).as_posix()])
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to read symlink at {rel_path}!")
            raise excp
        return Path(stdout.strip())

    def file_exists(self, rel_path: str | Path) -> bool:
        p = self.run(["test", "-e", self.path(rel_path).as_posix()], check=False)
        return p.returncode == 0

    def is_file(self, rel_path: str | Path) -> bool:
        return self.run(["test", "-f", self.path(rel_path).as_posix()], check=False).returncode == 0

    def is_dir(self, rel_path: str | Path) -> bool:
        return self.run(["test", "-d", self.path(rel_path).as_posix()], check=False).returncode == 0

    def file_mode(self, rel_path: str | Path) -> int:
        return int(
            self.check_output(["stat", "-c", "%f", self.path(rel_path).as_posix()]).rstrip(),
            base=16,
        )

    def file_timestamp(self, rel_path: str | Path) -> int:
        return int(self.check_output(["stat", "-c", "%Y", self.path(rel_path).as_posix()]).rstrip())

    def inode(self, rel_path: str | Path) -> int:
        return int(self.check_output(["stat", "-c", "%i", self.path(rel_path).as_posix()]).rstrip())

    def makedirs(self, rel_path: str | Path) -> None:
        makedirs(self.path(rel_path), sudo=True, substitute_user=self.id)

    def reset_admin_password(self, new_password: str | None = None) -> None:
        self.run(["cmk-passwd", "-i", ADMIN_USER], input_=new_password or self.admin_password)

    def listdir(self, rel_path: str | Path) -> list[str]:
        output = self.check_output(["ls", "-1", self.path(rel_path).as_posix()])
        return output.strip().split("\n") if output else []

    def system_temp_dir(self) -> Iterator[str]:
        stdout = self.check_output(["mktemp", "-d", "cmk-system-test-XXXXXXXXX", "-p", "/tmp"])  # nosec
        path = stdout.strip()

        try:
            yield path
        finally:
            try:
                _ = self.run(["rm", "-rf", path])
            except subprocess.CalledProcessError as excp:
                excp.add_note(f"Failed to delete directory '{path}'!")
                raise excp

    def cleanup_if_wrong_version(self) -> None:
        if not self.exists():
            return

        if self.current_version_directory() == self._package.version_directory():
            return

        # Now cleanup!
        self.rm()

    def current_version_directory(self) -> str:
        return os.path.split(os.readlink("/omd/sites/%s/version" % self.id))[-1]

    @tracer.instrument("Site.install_cmk")
    def install_cmk(self) -> None:
        """Install the Checkmk version of the site if it is not installed already."""
        if not self._package.is_installed():
            logger.info("Installing Checkmk version %s", self._package.version_directory())
            try:
                _ = run(
                    [
                        f"{repo_path()}/scripts/run-uvenv",
                        f"{repo_path()}/tests/scripts/install-cmk.py",
                        "--old-edition-name" if isinstance(self.package, CMKPackageInfoOld) else "",
                    ],
                    env=dict(os.environ, VERSION=self.version.version, EDITION=self.edition.short),
                )
            except subprocess.CalledProcessError as excp:
                excp.add_note("Execute 'tests/scripts/install-cmk.py' manually to debug the issue.")
                excp.add_note(excp.stdout)
                excp.add_note(excp.stderr)
                if excp.returncode == 22:
                    raise RuntimeError(
                        f"Version {self.version.version} could not be installed!"
                    ) from excp
                if excp.returncode == 11:
                    raise FileNotFoundError(
                        f"Version {self.version.version} could not be downloaded!"
                    ) from excp
                raise excp

    @tracer.instrument("Site.uninstall_cmk")
    def uninstall_cmk(self) -> None:
        """Uninstall the Checkmk package corresponding to the site, if it was not preinstalled."""
        if self.exists() and self._package.version == self.version:
            raise RuntimeError(
                f"Site {self.id} is currently running with cmk version "
                f"{self.version.version}. Please remove or update the site before "
                f"uninstalling the cmk package."
            )
        if self._package.is_installed() and not self._package_was_preinstalled:
            logger.info("Uninstalling Checkmk package %s", self._package.version_directory())
            try:
                _ = run(
                    [
                        f"{repo_path()}/scripts/run-uvenv",
                        f"{repo_path()}/tests/scripts/install-cmk.py",
                        "--uninstall",
                        "--old-edition-name" if isinstance(self.package, CMKPackageInfoOld) else "",
                    ],
                    env=dict(os.environ, VERSION=self.version.version, EDITION=self.edition.short),
                )
            except subprocess.CalledProcessError as excp:
                excp.add_note(
                    "Execute 'tests/scripts/install-cmk.py --uninstall [--old-edition-name]' "
                    "manually to debug the issue."
                )
                if excp.returncode == 22:
                    raise RuntimeError(
                        f"Package '{self._package}' could not be uninstalled!"
                    ) from excp
                raise excp
            output = run(
                ["ls", "-laR", self._package.version_path()], check=False, sudo=True
            ).stdout
            remaining_files = [_ for _ in output.strip().split("\n") if _]
            assert not remaining_files, (
                f"Package '{self._package}' is still installed, "
                "even though the uninstallation was completed with RC=0!"
                f"Remaining files: {remaining_files}"
            )

    @tracer.instrument("Site.create")
    def create(self) -> None:
        self.install_cmk()

        if not self.reuse and self.exists():
            raise Exception("The site %s already exists." % self.id)

        if not self.exists():
            logger.info('Creating site "%s"', self.id)
            completed_process = run(
                (
                    [
                        "omd",
                        "-V",
                        self._package.version_directory(),
                        "create",
                        "--admin-password",
                        self.admin_password,
                        "--apache-reload",
                        self.id,
                    ]
                ),
                check=False,
                sudo=True,
            )
            assert not completed_process.returncode, completed_process.stderr
            assert self.exists(), "Site %s was not created!" % self.id

            self._ensure_sample_config_is_present()
            # This seems to cause an issue with GUI and XSS crawl (they take too long or seem to
            # hang) job. Disable as a quick fix. We may have to parametrize this per job type.
            # self._set_number_of_apache_processes()
            if not self.edition.is_community_edition():
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

        self.openapi.port = self.apache_port
        # set the sites timezone according to TZ
        self.set_timezone(os.getenv("TZ", "UTC"))

        self._disable_autostart()

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
        ]

        missing = []
        for f in required_files:
            if not self.file_exists(f):
                missing.append(f)
        return missing

    def _update_cmk_core_config(self) -> None:
        logger.info("Updating core configuration...")
        _ = self.run(["cmk", "-U"])

    def _enable_liveproxyd_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/liveproxyd.d")
        # 15 = verbose
        # 10 = debug
        self.write_file(
            "etc/check_mk/liveproxyd.d/logging.mk", "liveproxyd_log_levels = {'cmk.liveproxyd': 15}"
        )

    def _enable_mkeventd_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/mkeventd.d")
        self.write_file(
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

        self.write_file(
            "etc/default/cmc",
            f'CMC_DAEMON_PREPEND="/opt/bin/valgrind --tool={tool} --quiet '
            f'--log-file=$OMD_ROOT/var/log/cmc-{tool}.log"\n',
        )

    def _set_number_of_apache_processes(self) -> None:
        self.makedirs("etc/apache/conf.d")
        self.write_file(
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
        self.write_file(
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
        self.write_file("etc/check_mk/conf.d/cmc-core-dumps.mk", "cmc_dump_core = True\n")

    def _enable_cmc_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/conf.d")
        self.write_file(
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
        self.write_file(
            "etc/check_mk/conf.d/cmc-log-rotation.mk",
            "cmc_log_rotation_method = 4\ncmc_log_limit = 1073741824\n",
        )

    def _enable_gui_debug_logging(self) -> None:
        self.makedirs("etc/check_mk/multisite.d")
        # 10: debug
        # 15: verbose
        # 20: informational
        # 30: warning (default)
        self.write_file(
            "etc/check_mk/multisite.d/logging.mk",
            "log_levels = %r\n"
            % {
                "cmk.web": 15,
                "cmk.web.ldap": 15,
                "cmk.web.saml2": 15,
                "cmk.web.auth": 15,
                "cmk.web.bi.compilation": 15,
                "cmk.web.automations": 15,
                "cmk.web.background-job": 15,
                "cmk.web.ui-job-scheduler": 10,
            },
        )

    def _tune_nagios(self) -> None:
        self.write_file(
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

    @tracer.instrument("Site.rm")
    def rm(self, site_id: str | None = None) -> None:
        # Wait a bit to avoid unnecessarily stress testing the site.
        site_id = site_id or self.id
        logger.info('Removing site "%s"...', site_id)
        time.sleep(1)
        _ = run(
            [
                "omd",
                "-f",
                "rm",
                "--apache-reload",
                "--kill",
                site_id,
            ],
            sudo=True,
        )

    @tracer.instrument("Site.start")
    def start(self) -> None:
        if not self.is_running():
            logger.info("Starting site")
            # start the site and ensure it's fully running (including all services)
            assert self.omd("start", check=True).returncode == 0
            # print("= BEGIN PROCESSES AFTER START ==============================")
            # self.execute(["ps", "aux"]).wait()
            # print("= END PROCESSES AFTER START ==============================")
            i = 0
            while not self.is_running():
                i += 1
                if i > 10:
                    self.omd("status")
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

        assert self.path("tmp").is_mount(), (
            "The site does not have a tmpfs mounted! We require this for good performing tests"
        )

    @tracer.instrument("Site.stop")
    def stop(self) -> None:
        if self.is_stopped():
            return  # Nothing to do
        logger.info("Stopping site")

        logger.debug("= BEGIN PROCESSES BEFORE =======================================")
        logger.debug(check_output(["ps", "-fwwu", str(self.id)]))
        logger.debug("= END PROCESSES BEFORE =======================================")

        stop_exit_code = self.omd("stop").returncode
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

        # let's ensure, that no more processes for the site are running (CMK-21668)
        # all site processes will be for some file below /omd/sites/<site_id>
        site_procs = get_processes_by_cmdline(f"omd/sites/{self.id}/")
        if site_procs:
            logger.warning(
                "processes still running after stopping the site %s (only first 10):", self.id
            )
            for proc in site_procs[:10]:
                logger.warning("  [%s] %s: %s", proc.pid, proc.info["name"], proc.info["cmdline"])
            if "--ignore-running-procs" in sys.argv:
                return
            raise AssertionError(
                "Site '%s' has still %d processes running after stopping!"
                % (self.id, len(site_procs))
            )

    def exists(self) -> bool:
        return os.path.exists("/omd/sites/%s" % self.id)

    @tracer.instrument("Site.ensure_running")
    def ensure_running(self) -> None:
        if not self.is_running():
            omd_status_output = self.check_output(["omd", "status"], stderr=subprocess.STDOUT)
            ps_output = self.check_output(["ps", "-ef"], stderr=subprocess.STDOUT)
            self.save_results()

            write_file(ps_output_file := self.result_dir / "processes.out", ps_output, sudo=True)

            self.report_crashes()

            pytest.exit(
                "Site was not running completely while it should be! Enforcing stop.\n\n"
                f"Output of omd status:\n{omd_status_output!r}\n\n"
                f'See "{ps_output_file}" for full "ps -ef" output!',
                returncode=1,
            )

    def is_running(self) -> bool:
        return self.omd("status").returncode == 0

    def wait_for_status_update(
        self,
        expected_status: int,
        timeout: int = 60,
        interval: int = 2,
    ) -> None:
        wait_until(
            lambda: self.omd("status").returncode == expected_status,
            timeout=timeout,
            interval=interval,
            condition_name="Site status update",
        )

    def activate_changes_and_wait_for_site_restart(
        self, timeout: int = 60, interval: int = 2
    ) -> None:
        """Activate changes which require a site restart and wait until the site is
        fully running again.
        """
        self.openapi.changes.activate()
        # first wait for the site to change the status to partially running
        self.wait_for_status_update(2, timeout, interval)
        # then wait for the site to be fully running
        self.wait_for_status_update(0, timeout, interval)

    def get_omd_service_names_and_statuses(self, service: str = "") -> dict[str, int]:
        """
        Return all service names and their statuses for the given site.
        """
        # Get all service names from 'omd status --bare <service>' command.
        cmd = ["status", "--bare"]
        if service:
            cmd.append(service)
        p = self.omd(*cmd, check=False)
        services = {}
        for line in p.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] != "OVERALL":
                try:
                    services[parts[0]] = int(parts[1])
                except ValueError as e:
                    raise ValueError(
                        f"Expected status code to be an integer for service {parts[0]}"
                    ) from e
        if not services:
            raise RuntimeError(
                f"No status found for '{' '.join(cmd)}'!\nSTDOUT:\n{p.stdout}\n",
                f"STDERR:\n{p.stderr}\n",
            )
        return services

    def is_stopped(self) -> bool:
        # 0 -> fully running
        # 1 -> fully stopped
        # 2 -> partially running
        return self.omd("status").returncode == 1

    @contextmanager
    def omd_stopped(self) -> Iterator[None]:
        """Make sure the site is stopped in this context.

        Start it afterwards in case it was running before.
        Fails if the site is partially running to begin with.
        """
        # fail for partially running sites.
        assert (omd_status := self.omd("status").returncode) in (0, 1)

        if omd_status == 1:  # stopped anyway
            yield
            return

        assert self.omd("stop").returncode == 0
        try:
            yield
        finally:
            assert self.omd("start").returncode == 0

    @contextmanager
    def omd_config(self, setting: str, value: str) -> Iterator[None]:
        """Set an omd config value for a context.

        This context manager will leave the site with the omd config set to the value
        it was before, in the state that it was before (running / stopped).
        """
        if (current_value := self.get_config(setting)) == value:
            yield
            return

        with self.omd_stopped():
            assert self.omd("config", "set", setting, value).returncode == 0

        try:
            yield
        finally:
            with self.omd_stopped():
                assert self.omd("config", "set", setting, current_value).returncode == 0

    def set_config(self, key: str, val: str, with_restart: bool = False) -> None:
        if self.get_config(key) == val:
            logger.info("omd config: %s is already at %r", key, val)
            return

        if with_restart:
            logger.debug("Stopping site")
            self.stop()

        logger.info("omd config: Set %s to %r", key, val)
        assert self.omd("config", "set", key, val).returncode == 0

        if with_restart:
            self.start()
            logger.debug("Started site")

    def get_config(self, key: str, default: str = "") -> str:
        process = self.omd("config", "show", key, check=True)
        logger.debug("omd config: %s is set to %r", key, stdout := process.stdout.strip())
        if stderr := process.stderr:
            logger.error(stderr)
        return stdout.strip() or default

    def core_name(self) -> Literal["cmc", "nagios"]:
        return "nagios" if self.edition.is_community_edition() else "cmc"

    def core_history_log(self) -> Path:
        core = self.core_name()
        if core == "nagios":
            return self.path("var/log/nagios.log")
        if core == "cmc":
            return self.path("var/check_mk/core/history")
        raise ValueError(f"Unhandled core: {core}")

    def core_history_log_timeout(self) -> int:
        return 10 if self.core_name() == "cmc" else 30

    def _create_automation_user(self, username: str) -> None:
        self._automation_secret = Password.random(24)
        if self.openapi.users.get(username):
            logger.info("Reusing existing test-user: '%s' (REUSE=1); resetting password.", username)
            self.run(
                ["bash", "-c", f'cmk-passwd "{username}" -i <<< "{self._automation_secret.raw}"']
            )
        else:
            logger.info("Creating test-user: '%s'.", username)
            self.openapi.users.create(
                username=username,
                fullname="Automation user for tests",
                password=self._automation_secret.raw,
                email="automation@localhost",
                contactgroups=[],
                roles=["admin"],
                is_automation_user=True,
            )
        self.openapi.set_authentication_header(user=username, password=self._automation_secret.raw)
        self.openapi_agent_receiver.set_authentication_header(
            user=username, password=self._automation_secret.raw
        )

    @tracer.instrument("Site.prepare_for_tests")
    def prepare_for_tests(self) -> None:
        logger.info("Prepare for tests")
        username = AUTOMATION_USER
        self._create_automation_user(username)
        if self.enforce_english_gui:
            web = CMKWebSession(self)
            if not self.edition.is_cloud_edition():
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
        try:
            # Try to create the ruleset with the new API.
            self.openapi.rules.create(
                ruleset_name="fileinfo_groups",
                value={
                    "group_patterns": [
                        {
                            "group_name": "TESTGROUP",
                            "pattern_configs": {
                                "include_pattern": "*gwia*",
                                "exclude_pattern": "",
                            },
                        }
                    ],
                },
                folder="/",
            )
        except Exception:
            # Fallback to the old API in case the new API is not available.
            self.openapi.rules.create(
                ruleset_name="fileinfo_groups",
                value={"group_patterns": [("TESTGROUP", ("*gwia*", ""))]},
                folder="/",
            )

    def enforce_non_localized_gui(self, web: CMKWebSession) -> None:
        r = web.get("user_profile.py")
        assert "Edit profile" in r.text, "Body: %s" % r.text

        if (user := self.openapi.users.get(ADMIN_USER)) is None:
            raise Exception("User cmkadmin not found!")
        user_spec, etag = user
        user_spec["language"] = "en"
        user_spec.pop("enforce_password_change", None)
        # TODO: DEPRECATED(18295) remove "mega_menu_icons"
        # Response contains "mega_menu_icons" AND "main_menu_icons" only _one_ is allowed in a request.
        user_spec["interface_options"].pop("mega_menu_icons", None)
        self.openapi.users.edit(ADMIN_USER, user_spec, etag)

        # Verify the language is as expected now
        r = web.get("user_profile.py", allow_redirect_to_login=True)
        assert "Edit profile" in r.text, "Body: %s" % r.text

    def send_traces_to_central_collector(self, endpoint: str) -> None:
        """Configure the site to send traces to our central collector"""
        logger.info("Send traces to central collector (collector: %s)", endpoint)
        self.set_config("TRACE_SEND", "on")
        self.set_config("TRACE_SEND_TARGET", endpoint)

    def write_resource_config(self, extra_resource_attributes: Mapping[str, str]) -> None:
        self.write_file(
            "etc/omd/resource_attributes_from_config.json",
            json.dumps(extra_resource_attributes) + "\n",
        )

    def open_livestatus_tcp(self, encrypted: bool) -> None:
        """This opens a currently free TCP port and remembers it in the object for later use
        Not free of races, but should be sufficient."""
        # Check if livestatus is already enabled and has correct TLS setting
        if self.get_config("LIVESTATUS_TCP").rstrip() == "on" and (
            self.get_config("LIVESTATUS_TCP_TLS", "off") == ("on" if encrypted else "off")
        ):
            return

        was_stopped = self.is_stopped()
        if not was_stopped:
            self.stop()
        self.set_config("LIVESTATUS_TCP", "on")
        self.gather_livestatus_port()
        self.set_config("LIVESTATUS_TCP_PORT", str(self._livestatus_port))
        # It might happen that OMD decides for another port (e.g. in case it is already in use).
        # So we need to read the port from the config again.
        self.gather_livestatus_port(from_config=True)
        self.set_config("LIVESTATUS_TCP_TLS", "on" if encrypted else "off")
        if not was_stopped:
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

    def _disable_autostart(self) -> None:
        self.set_config("AUTOSTART", "off", with_restart=False)

    def save_results(self) -> None:
        if not (is_containerized() or self.result_dir_from_env):
            logger.info("Not copying results (not containerized and undefined RESULT_PATH)")
            return

        logger.info("Saving to %s", self.result_dir)
        if self.path("junit.xml").exists():
            run(["cp", self.path("junit.xml").as_posix(), self.result_dir.as_posix()], sudo=True)

        run(["cp", "-rL", self.path("var/log").as_posix(), self.result_dir.as_posix()], sudo=True)

        # Rename apache logs to get better handling by the browser when opening a log file
        for log_name in ("access_log", "error_log"):
            orig_log_path = self.result_dir / "log" / "apache" / log_name
            if self.file_exists(orig_log_path):
                run(
                    [
                        "mv",
                        orig_log_path.as_posix(),
                        (orig_log_path.parent / log_name.replace("_", ".")).as_posix(),
                    ],
                    sudo=True,
                )

        for nagios_log_path in glob.glob(self.path("var/nagios/*.log").as_posix()):
            run(["cp", nagios_log_path, (self.result_dir / "log").as_posix()], sudo=True)

        core_dir = self.result_dir / self.core_name()
        makedirs(core_dir, sudo=True)

        run(
            [
                "cp",
                self.core_history_log().as_posix(),
                (core_dir / "history").as_posix(),
            ],
            sudo=True,
        )

        if self.file_exists("var/check_mk/core/core"):
            run(
                [
                    "cp",
                    self.path("var/check_mk/core/core").as_posix(),
                    (core_dir / "core_dump").as_posix(),
                ],
                sudo=True,
            )

        run(
            ["cp", "-r", self.crash_report_dir.as_posix(), self.crash_archive_dir.as_posix()],
            sudo=True,
        )

        run(
            [
                "cp",
                "-r",
                self.path("var/check_mk/background_jobs").as_posix(),
                self.result_dir.as_posix(),
            ],
            sudo=True,
        )

        # Change ownership of all copied files to the user that executes the test
        run(["chown", "-R", f"{os.getuid()}:{os.getgid()}", self.result_dir.as_posix()], sudo=True)

        # Rename files to get better handling by the browser when opening a crash file
        for crash_info in self.crash_archive_dir.glob("**/crash.info"):
            crash_json = crash_info.parent / (crash_info.stem + ".json")
            crash_info.rename(crash_json)

    def crash_reports_dirs(self) -> list[Path]:
        return [
            self.crash_report_dir / crash_type / crash_id
            for crash_type in self.listdir(self.crash_report_dir)
            for crash_id in self.listdir(self.crash_report_dir / crash_type)
        ]

    def report_crashes(self) -> None:
        logger.info(f"Checking crash reports for site {self.id}")
        for crash_dir in self.crash_reports_dirs():
            if crash_dir in self.known_crashes:
                continue
            self.known_crashes.add(crash_dir)
            crash_file = crash_dir / "crash.info"
            try:
                crash = json.loads(self.read_file(crash_file))
            except Exception:
                pytest_check.fail(f"Crash report detected!\nSee {crash_dir} for more details.")
                continue
            crash_type = crash.get("exc_type", "")
            crash_detail = crash.get("exc_value", "")
            if re.search("systime", crash_detail):
                logger.warning("Ignored crash report. See CMK-20674")
                continue
            if re.search("Licensed phase: too many services.", crash_detail):
                logger.warning("Ignored crash report due to license violation!")
                continue
            if re.search("SectionVMInfo", crash_detail):
                logger.warning("Ignored crash report due to CMK-27875.")
                continue
            pytest_check.fail(
                f"""Crash report detected! {crash_type}: {crash_detail}.
                See {crash_file} for more details."""
            )

    @property
    def result_dir_from_env(self) -> Path | None:
        return (
            Path(env_result_path) / self.id
            if (env_result_path := os.getenv("RESULT_PATH"))
            else None
        )

    @property
    def result_dir(self) -> Path:
        return self.result_dir_from_env or (repo_path() / "results" / self.id)

    @property
    def crash_report_dir(self) -> Path:
        return self.root / "var" / "check_mk" / "crashes"

    @property
    def crash_archive_dir(self) -> Path:
        return self.result_dir / "crashes"

    @property
    def logs_dir(self) -> Path:
        return self.root / "var" / "log"

    def get_automation_secret(self) -> str:
        if self._automation_secret is None:
            raise RuntimeError("Automation user was not created yet")
        return self._automation_secret.raw

    def get_site_internal_secret(self) -> Secret:
        secret_path = "etc/site_internal.secret"
        secret = self.read_file(secret_path, encoding=None)

        if secret == b"":
            raise Exception("Failed to read secret from %s" % secret_path)

        return Secret(secret)

    @tracer.instrument("Site.activate_changes_and_wait_for_core_reload")
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
            base_dir = site.path("var/check_mk/wato").as_posix()
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

            changed = self.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=allow_foreign_changes
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

    def read_global_settings(self, relative_path: Path) -> dict[str, object]:
        global_settings: dict[str, object] = {}
        exec(self.read_file(relative_path), {}, global_settings)  # nosec
        return global_settings

    def write_global_settings(
        self,
        relative_path: Path,
        global_settings: Mapping[str, object],
    ) -> None:
        self.write_file(
            relative_path,
            "\n".join(f"{key} = {repr(val)}" for key, val in global_settings.items()),
        )

    def update_global_settings(self, relative_path: Path, update: dict[str, object]) -> None:
        self.write_global_settings(
            relative_path,
            self.read_global_settings(relative_path) | update,
        )

    def read_site_specific_settings(
        self, relative_path: Path
    ) -> dict[str, dict[str, dict[str, object]]]:
        site_specific_settings: dict[str, dict[str, dict[str, object]]] = {"sites": {}}
        exec(self.read_file(relative_path), {}, site_specific_settings)  # nosec
        return site_specific_settings

    def write_site_specific_settings(
        self,
        relative_path: Path,
        site_specific_settings: Mapping[str, Mapping[str, object]],
    ) -> None:
        self.write_file(
            relative_path,
            "\n".join(f"{key} = {repr(val)}" for key, val in site_specific_settings.items()),
        )

    def update_site_specific_settings(
        self, relative_path: Path, update: Mapping[str, Mapping[str, object]]
    ) -> None:
        current_settings = self.read_site_specific_settings(relative_path)
        for site_id, updated_site_settings in update.items():
            if site_id not in current_settings["sites"]:
                current_settings["sites"][site_id] = {}
            current_settings["sites"][site_id].update(updated_site_settings)

        self.write_site_specific_settings(relative_path, current_settings)

    @contextmanager
    def backup_and_restore_files(self, files: list[Path]) -> Iterator[None]:
        """Backup file(s) when entering the context and restore them when exiting.

        Args:
            files: List of files to be backed up.
                Files are assumed to be relative to the site's root directory.
        """
        list_of_files = ", ".join(map(str, files))
        logger.info("Backup files: '%s'", list_of_files)
        backup = {file: self.read_file(file) for file in files}
        try:
            yield
        finally:
            logger.info("Restore files: '%s'", list_of_files)
            for file, content in backup.items():
                self.write_file(rel_path=file, content=content)
            self.openapi.changes.activate_and_wait_for_completion()

    def get_host_and_service_count(self) -> tuple[int, int]:
        """Helper function to get the count of hosts and services on a site.
        In case if connected remote site(s) exist(s), the hosts and services from it are also
        included into counts on central site.
        """
        host_names, services = self._get_existing_hosts_and_services()
        logger.debug(f"Found {len(host_names)} hosts on {self.id} site: {host_names}")
        logger.debug(f"Found {len(services)} services on {self.id} site: {services}")
        return len(host_names), len(services)

    def _get_existing_hosts_and_services(self) -> tuple[list[str], list[dict[str, Any]]]:
        """Helper function to get the existing hosts and services on a site.
        In case if connected remote site(s) exist(s), the hosts and services from it are also
        included into result lists on central site.
        """
        logger.info("Check for existing hosts on a site")
        host_names = self.openapi.hosts.get_all_names()
        total_services = []
        if host_names:
            logger.info("Found %d existing hosts on a site: %s", len(host_names), host_names)
            logger.info("Check how many services are configured on the existing hosts")
            for host_name in host_names:
                services = self.openapi.services.get_host_services(host_name)
                service_count = len(services)
                total_services += services
                logger.info("Host '%s' has %d services configured", host_name, service_count)
        else:
            logger.info(f"No existing hosts found on {self.id} site")
            host_names = []
        if not total_services:
            logger.info(f"No existing services found on {self.id} site")
        else:
            logger.info(
                f"Found a total of {len(total_services)} existing services on {self.id} site"
            )
        return host_names, total_services


@dataclass(frozen=True)
class GlobalSettingsUpdate:
    relative_path: Path
    update: dict[str, object]


class SiteFactory:
    """
    SiteFactory is a utility class for managing test sites in a Check_MK context.

    It supports creating, initializing, updating (both interactively and as a specific site user),
    copying, restoring, and removing sites - including multi-site environments.
    """

    def __init__(
        self,
        package: CMKPackageInfo | CMKPackageInfoOld,
        prefix: str | None = None,
        update: bool = False,
        update_conflict_mode: str = "install",
        enforce_english_gui: bool = True,
    ) -> None:
        self._package = package
        self._base_ident = prefix if prefix is not None else "s_%s_" % self.version.branch[:6]
        self._sites: dict[str, Site] = {}
        self._index = 1
        self._update = update
        self._update_conflict_mode = update_conflict_mode
        self._enforce_english_gui = enforce_english_gui

    @property
    def sites(self) -> Mapping[str, Site]:
        return self._sites

    @property
    def version(self) -> CMKVersion:
        return self._package.version

    @property
    def edition(self) -> TypeCMKEdition | TypeCMKEditionOld:
        return self._package.edition

    def get_site(self, name: str, create: bool = True) -> Site:
        site = self._site_obj(name)

        if self.edition.is_cloud_edition():
            # We need to create some Checkmk Cloud config files before starting the site, exactly as it
            # happens on the SaaS environment, where k8s takes care of creating the config files
            # before the site is created.
            create_cse_initial_config()
        if create:
            site.create()
        return site

    def initialize_site(
        self,
        site: Site,
        *,
        start: bool = True,
        init_livestatus: bool = True,
        prepare_for_tests: bool = True,
        activate_changes: bool = True,
        auto_restart_httpd: bool = False,
        tracing_config: TracingConfig = NO_TRACING,
    ) -> Site:
        if init_livestatus:
            site.open_livestatus_tcp(encrypted=False)
        if tracing_config.collect_traces:
            site.send_traces_to_central_collector(tracing_config.otlp_endpoint)
            if tracing_config.extra_resource_attributes:
                site.write_resource_config(tracing_config.extra_resource_attributes)

        if not start:
            return site

        site.start()

        if prepare_for_tests:
            with (
                cse_openid_oauth_provider(f"http://localhost:{site.apache_port}")
                if self.edition.is_cloud_edition()
                else nullcontext()
            ):
                site.prepare_for_tests()

        if activate_changes:
            # There seem to be still some changes that want to be activated
            # We created a user as AUTH_USER aka cmkadmin, meanwhile we are automationuser...
            site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)

        if auto_restart_httpd:
            restart_httpd()

        logger.debug("Created site %s", site.id)
        return site

    def setup_customers(self, site: Site, customers: Sequence[str]) -> None:
        if not self.edition.is_ultimatemt_edition():
            return
        customer_content = "\n".join(
            f"customers.update({{'{customer}': {{'name': '{customer}', 'macros': [], 'customer_report_layout': 'default'}}}})"
            for customer in customers
        )
        site.write_file("etc/check_mk/multisite.d/wato/customers.mk", customer_content)

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
            assert not site.exists(), (
                f"Site {name} already existing. Please remove it before restoring it from a backup."
            )

        try:
            site.install_cmk()
        except FileNotFoundError:
            pytest.skip(
                f"Base-version '{site.version.version}' is not available for distro "
                f"{os.environ.get('DISTRO')}"
            )
        logger.info("Creating %s site from backup...", name)

        omd_restore_cmd = (
            ["sudo", "omd", "restore", "--apache-reload"]
            + (["--reuse", "--kill"] if reuse else [])
            + [backup_path]
        )

        completed_process = subprocess.run(
            omd_restore_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )

        assert completed_process.returncode == 0, (
            f"Restoring site from backup failed!\n{completed_process.stdout.strip()}"
        )

        site = self.get_existing_site(site.id)
        site.start()
        restart_httpd()

        return site

    @contextmanager
    def copy_site(self, site: Site, copy_name: str) -> Iterator[Site]:
        site_copy = self._site_obj(copy_name)

        assert not site_copy.exists(), (
            f"Site '{copy_name}' already existing. Please remove it before performing a copy."
        )

        site.stop()
        logger.info("Copying site '%s' to site '%s'...", site.id, site_copy.id)
        run(["omd", "cp", site.id, site_copy.id], sudo=True)
        site_copy = self.get_existing_site(copy_name)
        site_copy.start()

        site.start()

        try:
            yield site_copy

        finally:
            if is_cleanup_enabled():
                logger.info("Removing site '%s'...", site_copy.id)
                site_copy.rm()

    def interactive_update(
        self,
        test_site: Site,
        target_package: CMKPackageInfo,
        min_version: CMKVersion,
        conflict_mode: str = "keepold",
        logfile_path: str = "/tmp/sep.out",  # nosec
        timeout: int = 60,
        abort: bool = False,
        failed_precheck: bool = False,
        disable_extensions: bool = False,
        n_extensions: int = 0,
        skip_if_version_not_supported: bool = True,
        license_ca_certificate: Certificate | None = None,
    ) -> Site:
        """Update the test-site with the given target-package, if supported.

        Such update process is performed interactively via Pexpect.

        Args:
            test_site:          The cmk site to be updated.
            target_package:     The target cmk package to update to.
            min_version:        The minimum cmk version supported for the update.
            conflict_mode:      The conflict mode for the update.
            logfile_path:       The path to the logfile.
            timeout:            The timeout for the expected dialog to appear during the update
                                process.
            abort:              If True, the abort dialog is expected to appear and the update
                                process will be aborted.
            failed_precheck:    If True, the precheck steps are expected to fail and the update
                                process will be aborted.
            disable_extensions: If True, installed cmk extensions (MKPs) will be disabled if the
                                corresponding dialog appears during the update process.
            n_extensions:       The expected number of extensions to be disabled during the update
                                process.
            skip_if_version_not_supported:
                                If True, the test will be skipped if the base version is not
                                supported for the update to the target version.
            license_ca_certificate:
                                The CA certificate to use for licensing: it will be replaced in the
                                target package during the update process so that the site can use
                                the mocked CA certificate for license validation.

        Returns:
            Site:              The updated site object.
        """
        base_package: CMKPackageInfo | CMKPackageInfoOld = test_site.package
        self._package = target_package

        # refresh site object to install the correct target version
        self._base_ident = ""
        site = self.get_existing_site(test_site.id, init_livestatus=False)

        site.install_cmk()
        site.stop()

        logger.info(
            "Updating '%s' site from '%s' version to '%s' version...",
            site.id,
            base_package.omd_version(),
            target_package.omd_version(),
        )

        pexpect_dialogs = []
        version_supported = base_package.version >= min_version
        if not version_supported and not skip_if_version_not_supported:
            pytest.fail(
                "Trying to update to an unsupported version.\n"
                f"Minimum supported version: {min_version}\n"
                f"Base version: {base_package.version}\n"
            )
        if version_supported:
            logger.info("Updating to a supported version.")
            pexpect_dialogs.extend(
                [
                    PExpectDialog(
                        expect=(
                            f"You are going to update the site {site.id} "
                            f"from version {base_package.omd_version()} "
                            f"to version {target_package.omd_version()}."
                        ),
                        send="u\r",
                    )
                ]
            )
        else:  # update-process not supported. Still, verify the correct message is displayed
            logger.info(
                "Updating '%s' site from version '%s' to version '%s' is not supported",
                site.id,
                base_package.omd_version(),
                target_package.omd_version(),
            )

            pexpect_dialogs.extend(
                [
                    PExpectDialog(
                        expect=(
                            f"ERROR: You are trying to update from "
                            f"{base_package.omd_version()} to "
                            f"{target_package.omd_version()} which is not supported."
                        ),
                        send="\r",
                    )
                ]
            )

        pexpect_dialogs.extend(
            [PExpectDialog(expect="Wrong permission", send="d", count=0, optional=True)]
        )

        if abort:
            pexpect_dialogs.extend([PExpectDialog(expect="Abort the update process?", send="A\r")])

        if disable_extensions:
            pexpect_dialogs.extend(
                [
                    PExpectDialog(
                        expect="disable the extension package",
                        send="d\r",
                        count=n_extensions,
                        optional=True,
                    )
                ]
            )

        with (
            replace_package_ca_certificate(
                package_root=Path(target_package.version_path()),
                ca_cert=license_ca_certificate,
            )
            if license_ca_certificate is not None
            else nullcontext()
        ):
            rc = spawn_expect_process(
                [
                    "/usr/bin/sudo",
                    "omd",
                    "-V",
                    target_package.version_directory(),
                    "update",
                    f"--conflict={conflict_mode}",
                    site.id,
                ],
                dialogs=pexpect_dialogs,
                logfile_path=logfile_path,
                timeout=timeout,
            )

        if abort:
            assert rc == 0, (
                f"Update process with aborted scenario failed.\n"
                "Logfile content:\n"
                f"{pprint.pformat(Path(logfile_path).read_text(), indent=4)}\n\n"
            )

            site.start()
            return site
        if failed_precheck:
            assert rc == 256, (
                f"Update process with failed precheck scenario did not fail as expected.\n"
                "Logfile content:\n"
                f"{pprint.pformat(Path(logfile_path).read_text(), indent=4)}\n\n"
            )
            return site
        if version_supported:
            assert rc == 0, (
                f"Failed to interactively update the test-site!\n"
                "Logfile content:\n"
                f"{pprint.pformat(Path(logfile_path).read_text(), indent=4)}\n\n"
                f"You might want to consider modifying {min_version=} to adapt it to the current "
                f"minimal supported version."
            )
        else:
            assert rc == 256, f"Executed command returned {rc} exit status. Expected: 256"
            pytest.skip(f"{base_package} is not a supported version for {target_package}")

        with open(logfile_path) as logfile:
            logger.debug("OMD automation logfile: %s", logfile.read())

        # refresh the site object after creating the site
        site = self.get_existing_site(test_site.id)

        assert site.version.version == target_package.version.version, (
            "Version mismatch after update process:\n"
            f"Expected version: {target_package.version.version}\n"
            f"Actual version: {site.version.version}"
        )

        _assert_tmpfs(site, base_package.version)
        if not site.edition.is_cloud_edition():
            _assert_nagvis_server(target_package)

        # start the site after manually installing it
        site.start()

        assert site.is_running(), "Site is not running!"
        logger.info("Site %s is up", site.id)

        restart_httpd()

        return site

    def update_as_site_user(
        self,
        test_site: Site,
        target_package: CMKPackageInfo = CMKPackageInfo(
            version_from_env(
                fallback_version_spec=CMKVersion.DAILY,
                fallback_branch=current_branch_name(),
            ),
            edition=edition_from_env(),
        ),
        min_version: CMKVersion = get_min_version(),
        conflict_mode: str = "keepold",
        start_site_after_update: bool = True,
        skip_if_version_not_supported: bool = True,
        license_ca_certificate: Certificate | None = None,
    ) -> Site:
        """
        Update the test-site with the given target-package.
        Such update process is performed as the site user.

        Args:
            license_ca_certificate:
                                The CA certificate to use for licensing: it will be replaced in the
                                target package during the update process so that the site can use
                                the mocked CA certificate for license validation.
        """
        base_package = test_site.package
        self._package = target_package

        version_supported = base_package.version >= min_version
        if not version_supported:
            if skip_if_version_not_supported:
                pytest.skip(
                    f"{base_package.version} is not a supported version for {target_package.version}"
                )
            else:
                pytest.fail(
                    "Trying to update to an unsupported version.\n"
                    f"Minimum supported version: {min_version}\n"
                    f"Base version: {base_package.version}\n"
                )

        # refresh site object to install the correct target version
        self._base_ident = ""
        site = self.get_existing_site(test_site.id, init_livestatus=False)

        site.install_cmk()
        site.stop()

        logger.info(
            "Updating %s site from %s to %s ...",
            site.id,
            base_package.omd_version(),
            target_package.omd_version(),
        )

        cmd = [
            "omd",
            "-f",
            "-V",
            target_package.version_directory(),
            "update",
            f"--conflict={conflict_mode}",
        ]

        with (
            replace_package_ca_certificate(
                package_root=Path(target_package.version_path()),
                ca_cert=license_ca_certificate,
            )
            if license_ca_certificate is not None
            else nullcontext()
        ):
            _ = site.run(cmd)

        # refresh the site object after creating the site
        site = self.get_existing_site(site.id)

        assert site.version.version == target_package.version.version, (
            "Version mismatch after update process:\n"
            f"Expected version: {target_package.version.version}\n"
            f"Actual version: {site.version.version}"
        )

        _assert_tmpfs(site, base_package.version)
        if not site.edition.is_cloud_edition():
            _assert_nagvis_server(target_package)

        if start_site_after_update:
            # start the site after manually installing it
            site.start()

            assert site.is_running(), "Site is not running!"
            logger.info("Site %s is up", site.id)

            restart_httpd()
            site.openapi.changes.activate_and_wait_for_completion()

        return site

    @contextmanager
    def get_test_site_ctx(
        self,
        name: str = "central",
        description: str = "",
        auto_cleanup: bool = True,
        auto_restart_httpd: bool = False,
        init_livestatus: bool = True,
        save_results: bool = True,
        report_crashes: bool = True,
        tracing_config: TracingConfig = NO_TRACING,
        global_settings_updates: Iterable[GlobalSettingsUpdate] = (),
    ) -> Iterator[Site]:
        yield from self.get_test_site(
            name=name,
            description=description,
            auto_cleanup=auto_cleanup,
            auto_restart_httpd=auto_restart_httpd,
            init_livestatus=init_livestatus,
            save_results=save_results,
            report_crashes=report_crashes,
            tracing_config=tracing_config,
            global_settings_updates=global_settings_updates,
        )

    def get_test_site(
        self,
        name: str = "central",
        description: str = "",
        auto_cleanup: bool = True,
        auto_restart_httpd: bool = False,
        init_livestatus: bool = True,
        save_results: bool = True,
        report_crashes: bool = True,
        tracing_config: TracingConfig = NO_TRACING,
        global_settings_updates: Iterable[GlobalSettingsUpdate] = (),
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
                if site.version != self.version:
                    # issue a warning if the version and/or edition differ
                    # we will still continue, as the tester/user might have a good reason for this
                    logger.warning(
                        "REUSE was set, but versions and/or editions differ. May cause issues."
                    )
                    logger.warning("  existing : version=%s).", site.version)
                    logger.warning("  requested: version=%s).", self.version)
            else:
                logger.info('Dropping existing site "%s" (REUSE=0)', site.id)
                site.rm()
        if not site.exists():
            site = self.get_site(name)

        try:
            self.setup_customers(site, ["customer1", "customer2"])
            for global_settings_update in global_settings_updates:
                site.update_global_settings(
                    global_settings_update.relative_path,
                    global_settings_update.update,
                )
            self.initialize_site(
                site,
                init_livestatus=init_livestatus,
                prepare_for_tests=True,
                tracing_config=tracing_config,
                auto_restart_httpd=auto_restart_httpd,
            )
            logger.info(
                'Site "%s" is ready!%s',
                site.id,
                f" [{description}]" if description else "",
            )
            with (
                cse_openid_oauth_provider(f"http://localhost:{site.apache_port}")
                if self.edition.is_cloud_edition()
                else nullcontext()
            ):
                yield site
        finally:
            if save_results:
                site.save_results()
            if report_crashes:
                site.report_crashes()
            if auto_cleanup and cleanup_site:
                logger.info('Dropping site "%s" (CLEANUP=1)', site.id)
                site.stop()
                site.rm()

    @contextmanager
    def connected_remote_site(
        self,
        site_name: str,
        central_site: Site,
        site_description: str = "",
        enable_replication: bool | None = None,
    ) -> Iterator[Site]:
        """Use a dynamically created, connected a remote site.

        Clean up site and connection during teardown.

        Args:
            site_name: The name of the remote site to be created.
            central_site: The central site to connect the new remote site to.
            site_description: The description text for the remote site.
            enable_replication: Specifies if replication will be enabled or not.
                By default, replication will be enabled for sites with matching editions.

        Yields:
            Site object for the connected remote site.
        """
        with self.get_test_site_ctx(
            site_name,
            description=site_description,
            auto_restart_httpd=True,
            tracing_config=tracing_config_from_env(os.environ),
        ) as remote_site:
            with connection(
                central_site=central_site,
                remote_site=remote_site,
                enable_replication=enable_replication,
            ):
                yield remote_site

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
            package=self._package,
            site_id=site_id,
            reuse=False,
            enforce_english_gui=self._enforce_english_gui,
        )

    def save_results(self) -> None:
        logger.info("Saving results")
        for _site_id, site in sorted(self._sites.items(), key=lambda x: x[0]):
            logger.info("Saving results of site %s", site.id)
            site.save_results()

    def report_crashes(self) -> None:
        logger.info("Reporting crashes")
        for _site_id, site in sorted(self._sites.items(), key=lambda x: x[0]):
            logger.info("Reporting crashes of site %s", site.id)
            site.report_crashes()

    def cleanup(self) -> None:
        logger.info("Removing sites")
        for site_id in list(self._sites.keys()):
            self.remove_site(site_id)


def get_site_factory(
    *,
    prefix: str,
    package: CMKPackageInfo | CMKPackageInfoOld | None = None,
    fallback_branch: str | Callable[[], str] | None = None,
) -> SiteFactory:
    """retrieves a correctly parameterized SiteFactory object

    This will be either
        * the default one (daily) or
        * as parameterized from the environment
    """
    package_info = package or CMKPackageInfo(
        version_from_env(
            fallback_version_spec=CMKVersion.DAILY,
            fallback_branch=fallback_branch,
        ),
        edition_from_env(),
    )
    logger.info(
        "Version: %s, Edition: %s, Branch: %s",
        package_info.version.version,
        package_info.edition.long,
        package_info.version.branch,
    )
    return SiteFactory(
        package=package_info,
        prefix=prefix,
    )


class PythonHelper:
    """Execute a python helper script executed in the site context

    Several tests need to execute some python code in the context
    of the Checkmk site under test. This object helps to copy
    and execute the script."""

    def __init__(self, site: Site, helper_path: Path, args: list[str] | None = None) -> None:
        self.site: Final = site
        self.helper_path: Final = helper_path
        self.site_path: Final = site.root / self.helper_path.name
        self.args: Final = args

    @contextmanager
    def copy_helper(self) -> Iterator[None]:
        self.site.write_file(
            str(self.site_path.relative_to(self.site.root)),
            self.helper_path.read_text(),
        )
        try:
            yield
        finally:
            self.site.delete_file(str(self.site_path))

    def check_output(
        self,
        input_: str | None = None,
        encoding: str = "utf-8",
    ) -> str:
        with self.copy_helper():
            output = self.site.check_output(
                ["python3", str(self.site_path)] + (self.args or []),
                input_=input_,
                encoding=encoding,
                stderr=subprocess.PIPE,
            )
            return output

    @contextmanager
    def execute(  # type: ignore[misc]
        self,
        preserve_env: list[str] | None = None,
        **kwargs: Any,
    ) -> Iterator[subprocess.Popen[str]]:
        with self.copy_helper():
            yield self.site.execute(
                ["python3", str(self.site_path)] + (self.args or []), preserve_env, **kwargs
            )


def _assert_tmpfs(site: Site, from_version: CMKVersion) -> None:
    # restoring the tmpfs was broken and has been fixed with
    # 3448a7da56ed6d4fa2c2f425d0b1f4b6e02230aa
    if (
        (CMKVersion("2.1.0p36") <= from_version < CMKVersion("2.2.0"))
        or (CMKVersion("2.2.0p13") <= from_version < CMKVersion("2.3.0"))
        or CMKVersion("2.3.0b1") <= from_version
    ):
        # tmpfs should have been restored:
        tmp_dirs = site.listdir("tmp/check_mk")
        assert "counters" in tmp_dirs
        assert "piggyback" in tmp_dirs
        assert "piggyback_sources" in tmp_dirs


def _assert_nagvis_server(package: CMKPackageInfo) -> None:
    nagvis_server_path = Path(
        f"/opt/omd/versions/{str(package)}/share/nagvis/htdocs/server/core/classes"
    )
    assert nagvis_server_path.exists()


def tracing_config_from_env(env: Mapping[str, str]) -> TracingConfig:
    return TracingConfig(
        collect_traces=(
            env.get("OTEL_SDK_DISABLED") != "true" and bool(env.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
        ),
        otlp_endpoint=env.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        extra_resource_attributes=_resource_attributes_from_env(env),
    )


def _resource_attributes_from_env(env: Mapping[str, str]) -> Mapping[str, str]:
    """Extract tracing resource attributes from the process environment

    This is meant to transport information exposed by the CI to tracing context in case the
    information is available. In case it is not there, be silent and don't expose the missing
    attribute.
    """
    return {
        name: val
        for name, val in [
            ("cmk.version.version", env.get("VERSION")),
            ("cmk.version.edition_short", env.get("EDITION")),
            ("cmk.version.branch", env.get("BRANCH")),
            ("cmk.version.distro", env.get("DISTRO")),
            ("cmk.ci.node_name", env.get("CI_NODE_NAME")),
            ("cmk.ci.workspace", env.get("CI_WORKSPACE")),
            ("cmk.ci.job_name", env.get("CI_JOB_NAME")),
            ("cmk.ci.build_number", env.get("CI_BUILD_NUMBER")),
            ("cmk.ci.build_url", env.get("CI_BUILD_URL")),
        ]
        if val
    }


@contextmanager
def connection(
    *, central_site: Site, remote_site: Site, enable_replication: bool | None = None
) -> Iterator[None]:
    """Set up the site connection between central and remote site for a distributed setup

    Args:
        central_site: The central site of the distributed setup.
        remote_site: The remote site to connect to.
        enable_replication: Specifies if replication will be enabled or not.
            By default, replication will be enabled for sites with matching editions.
    """
    basic_settings = {
        "alias": f"Remote site {remote_site.id}",
        "site_id": remote_site.id,
    }
    if central_site.edition.is_ultimatemt_edition():
        basic_settings["customer"] = "provider"
    if enable_replication is None:
        enable_replication = central_site.edition == remote_site.edition
    if enable_replication:
        configuration_connection = {
            "enable_replication": True,
            "url_of_remote_site": remote_site.internal_url,
            "disable_remote_configuration": True,
            "ignore_tls_errors": True,
            "direct_login_to_web_gui_allowed": True,
            "user_sync": {"sync_with_ldap_connections": "all"},
            "replicate_event_console": True,
            "replicate_extensions": True,
            "is_trusted": False,
        }
        # stay backwards-compatible for adding older remote sites:
        # only set message_broker_port for CMK2.4.0+
        if remote_site.version >= CMKVersion("2.4.0"):
            configuration_connection["message_broker_port"] = remote_site.message_broker_port
    else:
        configuration_connection = {
            "enable_replication": False,
        }
    site_config: dict[str, object] = {
        "basic_settings": basic_settings,
        "status_connection": {
            "connection": {
                "socket_type": "tcp",
                "host": remote_site.http_address,
                "port": remote_site.livestatus_port,
                "encrypted": False,
                "verify": False,
            },
            "proxy": {
                "use_livestatus_daemon": "direct",
            },
            "connect_timeout": 2,
            "persistent_connection": False,
            "url_prefix": f"/{remote_site.id}/",
            "status_host": {"status_host_set": "disabled"},
            "disable_in_status_gui": False,
        },
        "configuration_connection": configuration_connection,
    }
    logger.info("Create site connection from '%s' to '%s'", central_site.id, remote_site.id)
    central_site.openapi.sites.create(site_config)
    if configuration_connection.get("enable_replication"):
        # CMK-27517: login won't work when replication is disabled
        # CMK-27518: login won't work for the community edition (even if site URL is set via UI)
        logger.info("Establish site login '%s' to '%s'", central_site.id, remote_site.id)
        central_site.openapi.sites.login(remote_site.id)
    logger.info("Activating site setup changes")
    central_site.openapi.changes.activate_and_wait_for_completion(
        # this seems to be necessary to avoid sporadic CI failures
        force_foreign_changes=True,
    )
    try:
        logger.info("Connection from '%s' to '%s' established", central_site.id, remote_site.id)
        yield
    finally:
        if is_cleanup_enabled():
            logger.info("Remove site connection from '%s' to '%s'", central_site.id, remote_site.id)
            logger.info("Hosts left: %s", central_site.openapi.hosts.get_all_names())
            logger.info("Delete remote site connection '%s'", remote_site.id)
            central_site.openapi.sites.delete(remote_site.id)
            logger.info("Activating site removal changes")
            central_site.openapi.changes.activate_and_wait_for_completion(
                # this seems to be necessary to avoid sporadic CI failures
                force_foreign_changes=True,
            )


@contextmanager
def replace_package_ca_certificate(package_root: Path, ca_cert: Certificate) -> Iterator[None]:
    """Replace the license CA certificate in the given package."""
    ca_cert_file = package_root / "share" / "check_mk" / "licensing" / "ca-certificate.pem"
    ca_cert_backup = ca_cert_file.parent / f"{ca_cert_file.name}.bak"
    run(["cp", ca_cert_file.as_posix(), ca_cert_backup.as_posix()], check=False, sudo=True)
    try:
        write_file(ca_cert_file, ca_cert.dump_pem().bytes, sudo=True)
        yield
    finally:
        run(["cp", ca_cert_backup.as_posix(), ca_cert_file.as_posix()], sudo=True)
        run(["rm", ca_cert_backup.as_posix()], sudo=True)
