#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import json
import logging
import os
import subprocess
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest

from tests.testlib.agent import (
    agent_controller_daemon,
    clean_agent_controller,
    download_and_install_agent_package,
)
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_base_branch_name, current_branch_version
from tests.testlib.version import CMKVersion, version_gte

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--disable-interactive-mode",
        action="store_true",
        default=False,
        help="Disable interactive site creation and update. Use CLI instead.",
    )
    parser.addoption(
        "--latest-base-version",
        action="store_true",
        default=False,
        help="Use the latest base-version only.",
    )
    parser.addoption(
        "--store-lost-services",
        action="store_true",
        default=False,
        help="Store list of lost services in a json reference.",
    )


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    # minimal version supported for an update that can merge the configuration
    MIN_VERSION = os.getenv("MIN_VERSION", "2.2.0p8")

    with open(Path(__file__).parent.resolve() / "base_versions.json", "r") as f:
        BASE_VERSIONS_STR = json.load(f)

    BASE_VERSIONS = [
        CMKVersion(
            base_version_str,
            Edition.CEE,
            current_base_branch_name(),
            current_branch_version(),
        )
        for base_version_str in BASE_VERSIONS_STR
    ]
    IDS = [
        f"from_{base_version.omd_version()}_to_{os.getenv('VERSION', 'daily')}"
        for base_version in BASE_VERSIONS
    ]


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


def _get_site(version: CMKVersion, interactive: bool, base_site: Site | None = None) -> Site:
    """Install or update the test site with the given version.

    An update installation is done automatically when an optional base_site is given.
    By default, both installing and updating is done directly via spawn_expect_process()."""
    update = base_site is not None and base_site.exists()
    update_conflict_mode = "keepold"
    sf = SiteFactory(
        version=CMKVersion(
            version.version,
            version.edition,
            current_base_branch_name(),
            current_branch_version(),
        ),
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
        logfile_path = f"/tmp/omd_{'update' if update else 'install'}_{site.id}.out"

        if not os.getenv("CI", "").strip().lower() == "true":
            print(
                "\033[91m"
                "#######################################################################\n"
                "# This will trigger a SUDO prompt if run with a regular user account! #\n"
                "# NOTE: Using interactive password authentication will NOT work here! #\n"
                "#######################################################################"
                "\033[0m"
            )

        if update:
            sf.interactive_update(
                base_site,  # type: ignore
                version,
                CMKVersion(
                    BaseVersions.MIN_VERSION,
                    Edition.CEE,
                    current_base_branch_name(),
                    current_branch_version(),
                ),
            )
        else:  # interactive site creation
            site = sf.interactive_create(site.id, logfile_path)

    else:
        # use SiteFactory for non-interactive site creation/update
        site = sf.get_site("central")

    return site


def version_supported(version: str) -> bool:
    """Check if the given version is supported for updating."""
    return version_gte(version, BaseVersions.MIN_VERSION)


@pytest.fixture(
    name="test_site", params=BaseVersions.BASE_VERSIONS, ids=BaseVersions.IDS, scope="module"
)
def get_site(request: pytest.FixtureRequest) -> Generator[Site, None, None]:
    """Install the test site with the base version."""
    base_version = request.param

    if (
        request.config.getoption(name="--latest-base-version")
        and base_version.version != BaseVersions.BASE_VERSIONS[-1].version
    ):
        pytest.skip("Only latest base-version selected")

    if os.environ.get("DISTRO") in ("sles-15sp4", "sles-15sp5") and not version_gte(
        base_version.version, "2.2.0p8"
    ):
        pytest.skip(
            "Checkmk installation failing for missing `php7`. This is fixed starting from "
            "base-version 2.2.0p8"
        )

    interactive_mode_off = request.config.getoption(name="--disable-interactive-mode")
    logger.info("Setting up test-site (interactive-mode=%s) ...", not interactive_mode_off)
    test_site = _get_site(base_version, interactive=not interactive_mode_off)
    yield test_site
    logger.info("Removing test-site...")
    test_site.rm()


def update_site(site: Site, target_version: CMKVersion, interactive_mode_off: bool) -> Site:
    """Update the test site to the target version."""
    logger.info("Updating site (interactive-mode=%s) ...", not interactive_mode_off)
    return _get_site(target_version, base_site=site, interactive=not interactive_mode_off)


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
