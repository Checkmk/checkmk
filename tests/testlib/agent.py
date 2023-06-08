#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import logging
import os
import socketserver
import subprocess
from collections.abc import Iterator
from multiprocessing import Process
from pathlib import Path

from tests.testlib import wait_until
from tests.testlib.site import Site
from tests.testlib.utils import execute

from cmk.utils.type_defs import HostName

logger = logging.getLogger(__name__)


def get_package_type() -> str:
    if os.path.exists("/var/lib/dpkg/status"):
        return "linux_deb"
    if (
        os.path.exists("/var/lib/rpm")
        and os.path.exists("/bin/rpm")
        or os.path.exists("/usr/bin/rpm")
    ):
        return "linux_rpm"
    raise NotImplementedError(
        "package_type recognition for the current environment is not supported yet. Please"
        " implement it if needed"
    )


def install_agent_package(package_path: Path) -> Path:
    package_type = get_package_type()
    installed_ctl_path = Path("/usr/bin/cmk-agent-ctl")
    if package_type == "linux_deb":
        execute(["sudo", "dpkg", "-i", package_path.as_posix()])
        return installed_ctl_path
    if package_type == "linux_rpm":
        execute(["sudo", "rpm", "-vU", "--oldpackage", "--replacepkgs", package_path.as_posix()])
        return installed_ctl_path
    raise NotImplementedError(
        f"Installation of package type {package_type} is not supported yet, please implement it"
    )


def download_and_install_agent_package(site: Site, tmp_dir: Path) -> Path:
    agent_download_resp = site.openapi.get(
        "domain-types/agent/actions/download_by_host/invoke",
        params={
            "agent_type": "generic",
            "os_type": get_package_type(),
        },
        headers={"Accept": "application/octet-stream"},
    )
    assert agent_download_resp.ok

    path_agent_package = tmp_dir / ("agent." + get_package_type())
    with path_agent_package.open(mode="wb") as tmp_agent_package:
        for chunk in agent_download_resp.iter_content(chunk_size=None):
            tmp_agent_package.write(chunk)

    return install_agent_package(path_agent_package)


def _is_containerized() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
        or os.environ.get("CMK_CONTAINERIZED") == "TRUE"
    )


class _CMKAgentSocketHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.sendall(
            subprocess.run(
                ["check_mk_agent"],
                input=self.request.recv(1024),
                capture_output=True,
                close_fds=True,
                check=True,
            ).stdout
        )


def _clear_controller_connections(ctl_path: Path) -> None:
    execute(["sudo", ctl_path.as_posix(), "delete-all"])


@contextlib.contextmanager
def _provide_agent_unix_socket() -> Iterator[None]:
    socket_address = Path("/run/check-mk-agent.socket")
    socket_address.unlink(missing_ok=True)
    proc = Process(
        target=socketserver.UnixStreamServer(
            server_address=str(socket_address),
            RequestHandlerClass=_CMKAgentSocketHandler,
        ).serve_forever
    )
    proc.start()
    socket_address.chmod(0o777)
    try:
        yield
    finally:
        proc.kill()
        socket_address.unlink(missing_ok=True)


@contextlib.contextmanager
def _run_controller_daemon(ctl_path: Path) -> Iterator[None]:
    # Note:
    # We are deliberately not using Popen as a context manager here. In case we run into an
    # exception while we are inside a Popen context manager, we end up in Popen.__exit__, which
    # waits for the child process to finish. Our child process is not supposed to ever finish.
    proc = subprocess.Popen(
        [
            ctl_path.as_posix(),
            "daemon",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        close_fds=True,
        encoding="utf-8",
    )

    try:
        yield
    finally:
        exit_code = proc.poll()
        proc.kill()

        stdout, stderr = proc.communicate()
        logger.info("Stdout from controller daemon process:\n%s", stdout)
        logger.info("Stderr from controller daemon process:\n%s", stderr)

        if exit_code is not None:
            logger.error("Controller daemon exited with code %s, which is unexpected.", exit_code)


@contextlib.contextmanager
def agent_controller_daemon(ctl_path: Path) -> Iterator[None]:
    """Manually take over systemds job if we are in a container (where we have no systemd)."""
    if not _is_containerized():
        yield
        return

    with _provide_agent_unix_socket(), _run_controller_daemon(ctl_path):
        yield


@contextlib.contextmanager
def clean_agent_controller(ctl_path: Path) -> Iterator[None]:
    _clear_controller_connections(ctl_path)
    try:
        yield
    finally:
        _clear_controller_connections(ctl_path)


def register_controller(
    contoller_path: Path,
    site: Site,
    hostname: HostName,
) -> None:
    execute(
        [
            "sudo",
            contoller_path.as_posix(),
            "register",
            "--server",
            site.http_address,
            "--site",
            site.id,
            "--hostname",
            hostname,
            "--user",
            "cmkadmin",
            "--password",
            site.admin_password,
            "--trust-cert",
        ]
    )


def wait_until_host_receives_data(
    site: Site,
    hostname: HostName,
    *,
    timeout: int = 120,
    interval: int = 20,
) -> None:
    wait_until(
        lambda: not site.execute(["cmk", "-d", hostname]).wait(),
        timeout=timeout,
        interval=interval,
    )
