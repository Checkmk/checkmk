#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import json
import logging
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

import pytest

from tests.testlib import CMKWebSession
from tests.testlib.agent import (
    agent_controller_daemon,
    clean_agent_controller,
    download_and_install_agent_package,
)
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_base_branch_name, PExpectDialog, spawn_expect_process
from tests.testlib.version import CMKVersion

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    BASE_VERSIONS_STR = [
        "2.2.0",
        "2.2.0p1",
        "2.2.0p2",
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


@pytest.fixture(
    name="test_site", params=BaseVersions.BASE_VERSIONS, ids=BaseVersions.IDS, scope="module"
)
def get_site(request: pytest.FixtureRequest) -> Site:
    """Install the test site with the base version."""
    base_version = request.param
    logger.info("Setting up test-site ...")
    return _get_site(base_version, interactive=True)


def update_site(site: Site, target_version: CMKVersion, interactive: bool = True) -> Site:
    """Update the test site to the target version."""
    return _get_site(target_version, base_site=site, interactive=interactive)


def reschedule_services(site: Site, hostname: str, max_count: int = 10) -> None:
    """Reschedule services in the test-site for a given host until no pending services are found."""

    count = 0
    base_data_host = get_host_data(site, hostname)

    # reschedule services
    site.schedule_check(hostname, "Check_MK", 0)

    while len(get_services_with_status(base_data_host, "PEND")) > 0 and count < max_count:
        logger.info(
            "The following services were found with pending status: %s. Rescheduling checks...",
            get_services_with_status(base_data_host, "PEND"),
        )
        site.schedule_check(hostname, "Check_MK", 0)
        base_data_host = get_host_data(site, hostname)
        count += 1


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(test_site: Site, tmp_path: Path) -> Path:
    return download_and_install_agent_package(test_site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state
