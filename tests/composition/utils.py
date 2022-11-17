#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import glob
import os
import socketserver
import subprocess
import time
from collections.abc import Iterator, Sequence
from multiprocessing import Process
from pathlib import Path

from tests.testlib.site import Site
from tests.testlib.utils import is_containerized

from tests.composition.constants import TEST_HOST_1


def wait_for_baking_job(central_site: Site, expected_start_time: float) -> None:
    waiting_time = 1
    waiting_cycles = 20
    for _ in range(waiting_cycles):
        time.sleep(waiting_time)
        baking_status = central_site.openapi.get_baking_status()
        assert baking_status.state in (
            "running",
            "finished",
        ), f"Unexpected baking state: {baking_status}"
        assert (
            baking_status.started >= expected_start_time
        ), f"No baking job started after expected starting time: {expected_start_time}"
        if baking_status.state == "finished":
            return
    raise AssertionError(
        f"Now waiting {waiting_cycles*waiting_time} seconds for baking job to finish, giving up..."
    )


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


def get_package_extension() -> str:
    package_type = get_package_type()
    if package_type == "linux_deb":
        return "deb"
    if package_type == "linux_rpm":
        return "rpm"
    raise NotImplementedError(
        f"'get_package_extension' for '{package_type}' is not supported yet in, please implement it"
    )


def execute(command: Sequence[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        command,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        capture_output=True,
        close_fds=True,
        check=False,
    )
    return proc


def install_agent_package(package_path: Path) -> Path:
    package_type = get_package_type()
    installed_ctl_path = Path("/usr/bin/cmk-agent-ctl")
    try:
        if package_type == "linux_deb":
            execute(["sudo", "dpkg", "-i", package_path.as_posix()]).check_returncode()
            return installed_ctl_path
        if package_type == "linux_rpm":
            execute(
                ["sudo", "rpm", "-vU", "--oldpackage", "--replacepkgs", package_path.as_posix()]
            ).check_returncode()
            return installed_ctl_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Error while installing cmk agent:\nstderr:\n{e.stderr}" f"\nstdout:\n{e.stdout}"
        ) from e
    raise NotImplementedError(
        f"Installation of package type {package_type} is not supported yet, please implement it"
    )


def bake_agent(site: Site) -> tuple[str, Path]:
    # Add test host
    start_time = time.time()
    site.openapi.create_host(
        TEST_HOST_1,
        attributes={"ipaddress": site.http_address},
        bake_agent=True,
    )

    site.activate_changes_and_wait_for_core_reload()

    # A baking job just got triggered automatically after adding the host. wait for it to finish.
    wait_for_baking_job(site, start_time)

    server_rel_hostlink_dir = Path("var", "check_mk", "agents", get_package_type(), "references")
    agent_path = site.resolve_path(server_rel_hostlink_dir / TEST_HOST_1)
    agent_hash = agent_path.name

    return agent_hash, agent_path


def get_cre_agent_path(site: Site) -> Path:
    # On CRE we can't bake agents since agent baking is a CEE feature so we use the vanilla agent
    package_extension = get_package_extension()
    agent_folder = site.resolve_path(Path("share", "check_mk", "agents"))
    # The locations of the 2 agent packages in the raw edition are:
    # *) $SITE_HOME/share/check_mk/agents/check-mk-agent_2022.11.08-1_all.deb
    # *) $SITE_HOME/share/check_mk/agents/check-mk-agent-2022.11.08-1.noarch.rpm
    agent_search_pattern = agent_folder / f"check-mk-agent*.{package_extension}"
    agent_results = list(glob.glob(agent_search_pattern.as_posix()))
    if not agent_results:
        raise ValueError(
            f"Can't find '{package_extension}' agent to install in folder '{agent_folder}'"
        )
    return Path(agent_results[0])


@contextlib.contextmanager
def clean_agent_controller(ctl_path: Path) -> Iterator[None]:
    _clear_controller_connections(ctl_path)
    yield
    _clear_controller_connections(ctl_path)


def _clear_controller_connections(ctl_path: Path) -> None:
    execute(["sudo", ctl_path.as_posix(), "delete-all"]).check_returncode()


@contextlib.contextmanager
def agent_controller_daemon(ctl_path: Path) -> Iterator[None]:
    """
    Manually take over systemds job if we are in a container (where we have no systemd). If this
    becomes too tedious to maintain, we should switch to running the tests using this
    functionality in a VM."""
    if not is_containerized():
        yield
        return

    if is_containerized():
        with _provide_agent_unix_socket(), _run_controller_daemon(ctl_path):
            yield


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
    yield None
    proc.kill()
    socket_address.unlink(missing_ok=True)


@contextlib.contextmanager
def _run_controller_daemon(ctl_path: Path) -> Iterator[None]:
    with subprocess.Popen(
        [
            "sudo",
            ctl_path.as_posix(),
            "daemon",
        ]
    ) as ctl_daemon_proc:
        yield
        ctl_daemon_proc.kill()


class _CMKAgentSocketHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.sendall(
            subprocess.run(
                ["sudo", "check_mk_agent"],
                input=self.request.recv(1024),
                capture_output=True,
                close_fds=True,
                check=True,
            ).stdout
        )


def should_skip_because_uncontainerized() -> bool:
    return not (is_containerized() or os.environ.get("OVERRIDE_UNCONTAINERIZED_SKIP"))
