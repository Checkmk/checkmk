#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import json
import logging
import os
import subprocess
from typing import Any, Optional

import pytest

from tests.testlib import CMKWebSession
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    BASE_VERSIONS = [
        CMKVersion("2.1.0p1", Edition.CEE, current_base_branch_name()),
        # CMKVersion("2.1.0p2", Edition.CEE, current_base_branch_name()),
        # CMKVersion("2.1.0p3", Edition.CEE, current_base_branch_name()),
        # ^those releases need htpasswd to set the admin password
        # CMKVersion("2.1.0p4", Edition.CEE, current_base_branch_name()),
        CMKVersion("2.1.0p5", Edition.CEE, current_base_branch_name()),
        CMKVersion("2.1.0p10", Edition.CEE, current_base_branch_name()),
        CMKVersion("2.1.0p20", Edition.CEE, current_base_branch_name()),
        # CMKVersion("2.1.0p21", Edition.CEE, current_base_branch_name()),
        # CMKVersion("2.1.0p22", Edition.CEE, current_base_branch_name()),
        CMKVersion("2.1.0p23", Edition.CEE, current_base_branch_name()),
    ]
    IDS = [
        f"from_{base_version.omd_version()}_to_{os.getenv('VERSION', 'daily')}"
        for base_version in BASE_VERSIONS
    ]


def get_host_data(site: Site) -> list[Any]:
    web = CMKWebSession(site)
    web.login()
    raw_data = json.loads(web.get("view.py?output_format=json_export&view_name=allhosts").content)
    data = []
    for item in raw_data[1:]:
        data.append({raw_data[0][i]: val} for i, val in enumerate(item))
    return data


def _run_as_site_user(
    site: Site, cmd: list[str], input_value: Optional[str] = None
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


def get_omd_version(site: Site, full: bool = False) -> str:
    cmd = ["/usr/bin/omd", "version", site.id]
    version = _run_as_site_user(site, cmd).stdout.split("\n", 1)[0]
    return version if full else version.rsplit(" ", 1)[-1]


def get_omd_status(site: Site) -> dict[str, str]:
    """Get the omd status for all services of the given site."""
    cmd = ["/usr/bin/omd", "status", "--bare"]
    status = {}
    for line in [_ for _ in _run_as_site_user(site, cmd).stdout.splitlines() if " " in _]:
        key, val = [_.strip() for _ in line.split(" ", 1)]
        status[key] = {"0": "running", "1": "stopped", "2": "partially running"}.get(val, val)
    return status


def get_site_status(site: Site) -> Optional[str]:
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


def _get_site(version: CMKVersion, update: bool) -> Site:
    """Install or update the test site with the given version."""

    sf = SiteFactory(
        version=CMKVersion(version.version, version.edition, current_base_branch_name()),
        prefix="update_",
        update_from_git=False,
        install_test_python_modules=False,
        update=update,
        update_conflict_mode="keepold",
        enforce_english_gui=False,
    )
    site = sf.get_existing_site("central")

    logger.info("Site exists: %s", site.exists())
    if site.exists():
        if not update:
            logger.info("Dropping existing site ...")
            site.rm()
        elif site.is_running():
            logger.info("Stopping running site before update ...")
            site.stop()
            assert get_site_status(site) == "stopped"
    if site.exists() == update:
        logger.info("Updating existing site" if update else "Creating new site")
        site = sf.get_site("central")

        web = CMKWebSession(site)
        try:
            web.login()
        except AssertionError:
            assert set_admin_password(site) == 0, "Could not set admin password!"
            logger.warning("Had to reset the admin password after installing %s!", version.version)
            site.stop()
            site.start()
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


@pytest.fixture(name="test_site", params=BaseVersions.BASE_VERSIONS, ids=BaseVersions.IDS)
def get_site(request: pytest.FixtureRequest) -> Site:
    """Install the test site with the base version."""
    base_version = request.param
    logger.info("Setting up test-site ...")
    return _get_site(base_version, update=False)


def update_site(target_version: CMKVersion) -> Site:
    """Update the test site to the target version."""
    return _get_site(target_version, update=True)
