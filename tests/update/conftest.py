#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import dataclasses
import json
import logging
import os
import socketserver
import subprocess
from collections.abc import Iterator, Sequence
from multiprocessing import Process
from pathlib import Path
from typing import Optional

import pytest

from tests.testlib import CMKWebSession
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_base_branch_name, PExpectDialog, spawn_expect_process
from tests.testlib.version import CMKVersion, version_gte

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    # minimal version supported for an update that can merge the configuration
    MIN_VERSION = os.getenv("MIN_VERSION", "2.1.0p20")
    BASE_VERSIONS_STR = [
        # "2.1.0p1",
        # "2.1.0p2",
        # "2.1.0p3", # ^those releases need htpasswd to set the admin password
        # "2.1.0p4",
        # "2.1.0p5",
        # "2.1.0p10",
        "2.1.0p20",
        "2.1.0p24",
    ]
    BASE_VERSIONS = [
        CMKVersion(base_version_str, Edition.CEE, current_base_branch_name())
        for base_version_str in BASE_VERSIONS_STR
    ]
    IDS = [
        f"from_{base_version.omd_version()}_to_{os.getenv('VERSION', 'daily')}"
        for base_version in BASE_VERSIONS
    ]


def get_host_data(site: Site, hostname: str) -> dict:
    """Return dict with key=service and value=status for all services in the given site and host."""
    web = CMKWebSession(site)
    web.login()
    raw_data = json.loads(
        web.get(
            f"view.py?host={hostname}&output_format=json_export&site={site.id}&view_name=host"
        ).content
    )
    data = {}
    for item in raw_data[1:]:
        data[item[1]] = item[0]
    return data


def get_services_with_status(
    host_data: dict, service_status: str, skipped_services: list | tuple = ()
) -> list:
    """Return a list of services in the given status which are not in the 'skipped' list."""
    service_list = []
    for service in host_data:
        if host_data[service] == service_status and service not in skipped_services:
            service_list.append(service)
    return service_list


def _run_as_site_user(
    site: Site, cmd: list[str], input_value: str | None = None
) -> subprocess.CompletedProcess:
    """Run a command as the site user and return the completed_process."""
    cmd = ["/usr/bin/sudo", "-i", "-u", site.id] + cmd
    logger.info("Executing: %s", subprocess.list2cmdline(cmd))
    completed_process = subprocess.run(
        cmd,
        input=input_value,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        check=False,
    )
    return completed_process


def set_admin_password(site: Site, password: str = "cmk") -> int:
    """Set the admin password for the given site.
    Use cmk-passwd if available (or htpasswd otherwise)."""
    if os.path.exists(f"{site.root}/bin/cmk-passwd"):
        # recent checkmk versions: cmk-passwd
        cmd = [f"{site.root}/bin/cmk-passwd", "-i", "cmkadmin"]
    else:
        # older checkmk versions: htpasswd
        cmd = ["/usr/bin/htpasswd", "-i", f"{site.root}/etc/htpasswd", "cmkadmin"]
    return _run_as_site_user(site, cmd, input_value=password).returncode


def verify_admin_password(site: Site) -> None:
    """Verify that logging in to the site is possible and reset the admin password otherwise."""
    web = CMKWebSession(site)
    try:
        web.login()
    except AssertionError:
        assert set_admin_password(site) == 0, "Could not set admin password!"
        logger.warning(
            "Had to reset the admin password after installing %s!", site.version.version_directory()
        )
        site.stop()
        site.start()


def get_omd_version(site: Site, full: bool = False) -> str:
    """Get the omd version for the given site."""
    cmd = ["/usr/bin/omd", "version", site.id]
    version = _run_as_site_user(site, cmd).stdout.split("\n", 1)[0]
    return version if full else version.rsplit(" ", 1)[-1]


def get_omd_status(site: Site) -> dict[str, str]:
    """Get the omd status for all services of the given site."""
    cmd = ["/usr/bin/omd", "status", "--bare"]
    status = {}
    for line in [_ for _ in _run_as_site_user(site, cmd).stdout.splitlines() if " " in _]:
        key, val = (_.strip() for _ in line.split(" ", 1))
        status[key] = {"0": "running", "1": "stopped", "2": "partially running"}.get(val, val)
    return status


def get_site_status(site: Site) -> str | None:
    """Get the overall status of the given site."""
    service_status = get_omd_status(site)
    logger.debug("Status codes: %s", service_status)
    if len(service_status) > 0:
        status = list(service_status.values())[-1]
        if status == "partially running":
            return status
        if status in ("running", "stopped") and all(
            value == status for value in service_status.values()
        ):
            return status
        logger.error("Invalid service status: %s", service_status)
    return None


def update_config(site: Site) -> int:
    """Run cmk-update-config and check the result.

    If merging the config worked fine, return 0.
    If merging the config was not possible, use installation defaults and return 1.
    If any other error occurred, return 2.
    """
    for rc, conflict_mode in enumerate(("abort", "install")):
        cmd = [f"{site.root}/bin/cmk-update-config", "-v", f"--conflict={conflict_mode}"]
        completed_process = _run_as_site_user(site, cmd)
        if completed_process.returncode == 0:
            logger.debug(completed_process.stdout)
            return rc
        logger.error(completed_process.stdout)
    return 2


def _get_site(
    version: CMKVersion, base_site: Optional[Site] = None, interactive: bool = True
) -> Site:
    """Install or update the test site with the given version.
    An update installation is done automatically when an optional base_site is given.
    By default, both installing and updating is done directly via spawn_expect_process()."""
    update = base_site is not None and base_site.exists()
    update_conflict_mode = "keepold"
    sf = SiteFactory(
        version=CMKVersion(version.version, version.edition, current_base_branch_name()),
        prefix="update_",
        update_from_git=False,
        update=update,
        update_conflict_mode=update_conflict_mode,
        enforce_english_gui=False,
    )
    site = sf.get_existing_site("central")

    logger.info("Site exists: %s", site.exists())
    if site.exists() and not update:
        logger.info("Dropping existing site ...")
        site.rm()
    elif site.is_running():
        logger.info("Stopping running site before update ...")
        site.stop()
        assert get_site_status(site) == "stopped"
    assert site.exists() == update, (
        "Trying to update non-existing site!" if update else "Trying to install existing site!"
    )
    logger.info("Updating existing site" if update else "Creating new site")

    if interactive:
        # bypass SiteFactory for interactive installations
        source_version = base_site.version.version_directory() if base_site else ""
        target_version = version.version_directory()
        logfile_path = f"/tmp/omd_{'update' if update else 'install'}_{site.id}.out"
        # install the release
        site.install_cmk()

        # Run the CLI installer interactively and respond to expected dialogs.

        if not os.getenv("CI", "").strip().lower() == "true":
            print(
                "\033[91m"
                "#######################################################################\n"
                "# This will trigger a SUDO prompt if run with a regular user account! #\n"
                "# NOTE: Using interactive password authentication will NOT work here! #\n"
                "#######################################################################"
                "\033[0m"
            )
        rc = spawn_expect_process(
            [
                "/usr/bin/sudo",
                "/usr/bin/omd",
                "-V",
                target_version,
                "update",
                f"--conflict={update_conflict_mode}",
                site.id,
            ]
            if update
            else [
                "/usr/bin/sudo",
                "/usr/bin/omd",
                "-V",
                target_version,
                "create",
                "--admin-password",
                site.admin_password,
                "--apache-reload",
                site.id,
            ],
            [
                PExpectDialog(
                    expect=(
                        f"You are going to update the site {site.id} "
                        f"from version {source_version} "
                        f"to version {target_version}."
                    ),
                    send="u\r",
                ),
                PExpectDialog(expect="Wrong permission", send="d", count=0, optional=True),
            ]
            if update
            else [],
            logfile_path=logfile_path,
        )

        assert rc == 0, f"Executed command returned {rc} exit status. Expected: 0"

        with open(logfile_path, "r") as logfile:
            logger.debug("OMD automation logfile: %s", logfile.read())
        # refresh the site object after creating the site
        site = sf.get_existing_site("central")
        # open the livestatus port
        site.open_livestatus_tcp(encrypted=False)
        # start the site after manually installing it
        site.start()
    else:
        # use SiteFactory for non-interactive site creation/update
        site = sf.get_site("central")

    verify_admin_password(site)

    assert site.is_running(), "Site is not running!"
    logger.info("Test-site %s is up", site.id)

    site_version, site_edition = get_omd_version(site).rsplit(".", 1)
    assert (
        site.version.version == version.version == site_version
    ), "Version mismatch during %s!" % ("update" if update else "installation")
    assert (
        site.version.edition.short == version.edition.short == site_edition
    ), "Edition mismatch during %s!" % ("update" if update else "installation")

    return site


def version_supported(version: str) -> bool:
    """Check if the given version is supported for updating."""
    return version_gte(version, BaseVersions.MIN_VERSION)


@pytest.fixture(name="test_site", params=BaseVersions.BASE_VERSIONS, ids=BaseVersions.IDS)
def get_site(request: pytest.FixtureRequest) -> Site:
    """Install the test site with the base version."""
    base_version = request.param
    logger.info("Setting up test-site ...")
    return _get_site(base_version, interactive=True)


def update_site(site: Site, target_version: CMKVersion, interactive: bool = True) -> Site:
    """Update the test site to the target version."""
    return _get_site(target_version, base_site=site, interactive=interactive)


def _execute(command: Sequence[str]) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            command,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
            capture_output=True,
            close_fds=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Subprocess terminated non-successfully. Stdout:\n{e.stdout}\nStderr:\n{e.stderr}"
        ) from e
    return proc


def _get_package_type() -> str:
    if os.path.exists("/var/lib/dpkg/status"):
        return "deb"
    if (
        os.path.exists("/var/lib/rpm")
        and os.path.exists("/bin/rpm")
        or os.path.exists("/usr/bin/rpm")
    ):
        return "rpm"
    raise NotImplementedError(
        "package_type recognition for the current environment is not supported yet. Please"
        " implement it if needed"
    )


def _install_agent_package(package_path: Path) -> Path:
    package_type = "linux_" + _get_package_type()
    installed_ctl_path = Path("/usr/bin/cmk-agent-ctl")
    if package_type == "linux_deb":
        _execute(["sudo", "dpkg", "-i", package_path.as_posix()])
        return installed_ctl_path
    if package_type == "linux_rpm":
        _execute(["sudo", "rpm", "-vU", "--oldpackage", "--replacepkgs", package_path.as_posix()])
        return installed_ctl_path
    raise NotImplementedError(
        f"Installation of package type {package_type} is not supported yet, please implement it"
    )


def download_and_install_agent_package(site: Site, tmp_dir: Path) -> Path:
    agent_download_resp = site.openapi.get(
        "domain-types/agent/actions/download_by_host/invoke",
        params={
            "agent_type": "generic",
            "os_type": "linux_" + _get_package_type(),
        },
        headers={"Accept": "application/octet-stream"},
    )
    assert agent_download_resp.ok

    path_agent_package = tmp_dir / ("agent." + _get_package_type())
    with path_agent_package.open(mode="wb") as tmp_agent_package:
        for chunk in agent_download_resp.iter_content(chunk_size=None):
            tmp_agent_package.write(chunk)

    return _install_agent_package(path_agent_package)


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


def _clear_controller_connections(ctl_path: Path) -> None:
    _execute(["sudo", ctl_path.as_posix(), "delete-all"])


@contextlib.contextmanager
def clean_agent_controller(ctl_path: Path) -> Iterator[None]:
    _clear_controller_connections(ctl_path)
    try:
        yield
    finally:
        _clear_controller_connections(ctl_path)
