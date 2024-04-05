#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import itertools
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
from tests.testlib.utils import current_base_branch_name, current_branch_version, restart_httpd
from tests.testlib.version import CMKVersion, get_min_version, version_gte

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


def pytest_configure(config):
    config.addinivalue_line("markers", "cee: marks tests using an enterprise-edition site")
    config.addinivalue_line("markers", "cce: marks tests using a cloud-edition site")


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    MIN_VERSION = get_min_version()

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


@dataclasses.dataclass
class TestParams:
    """Pytest parameters used in the test."""

    INTERACTIVE_MODE = [True, False]
    TEST_PARAMS = [
        pytest.param(
            (base_version, interactive_mode),
            id=f"base-version={base_version.version}|interactive-mode={interactive_mode}",
        )
        for base_version, interactive_mode in itertools.product(
            BaseVersions.BASE_VERSIONS, INTERACTIVE_MODE
        )
        # interactive mode enabled for some specific distros
        if interactive_mode == (os.environ.get("DISTRO") in ["ubuntu-22.04", "almalinux-9"])
    ]


def get_omd_status(site: Site) -> dict[str, str]:
    """Get the omd status for all services of the given site."""
    cmd = ["/usr/bin/omd", "status", "--bare"]
    status = {}
    process = site.execute(cmd, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for line in [_ for _ in stdout.splitlines() if " " in _]:
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


def _get_site(version: CMKVersion, interactive: bool, base_site: Site | None = None) -> Site:
    """Install or update the test site with the given version.

    An update installation is done automatically when an optional base_site is given.
    By default, both installing and updating is done directly via spawn_expect_process()."""
    update = base_site is not None and base_site.exists()
    update_conflict_mode = "keepold"
    min_version = CMKVersion(
        BaseVersions.MIN_VERSION,
        Edition.CEE,
        current_base_branch_name(),
        current_branch_version(),
    )
    sf = SiteFactory(
        version=CMKVersion(
            version.version,
            version.edition,
            current_base_branch_name(),
            current_branch_version(),
        ),
        prefix="update_",
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
                target_version=version,
                min_version=min_version,
            )
        else:  # interactive site creation
            try:
                site = sf.interactive_create(site.id, logfile_path)
                restart_httpd()
            except Exception as e:
                if f"Version {version.version} could not be installed" in str(e):
                    pytest.skip(
                        f"Base-version {version.version} not available in "
                        f'{os.environ.get("DISTRO")}'
                    )
    else:
        if update:
            # non-interactive update as site-user
            sf.update_as_site_user(site, target_version=version, min_version=min_version)

        else:  # use SiteFactory for non-interactive site creation
            try:
                site = sf.get_site("central")
                restart_httpd()
            except Exception as e:
                if f"Version {version.version} could not be installed" in str(e):
                    pytest.skip(
                        f"Base-version {version.version} not available in "
                        f'{os.environ.get("DISTRO")}'
                    )

    return site


def version_supported(version: str) -> bool:
    """Check if the given version is supported for updating."""
    return version_gte(version, BaseVersions.MIN_VERSION)


@pytest.fixture(name="test_setup", params=TestParams.TEST_PARAMS, scope="module")
def _setup(request: pytest.FixtureRequest) -> Generator[tuple, None, None]:
    """Install the test site with the base version."""
    base_version, interactive_mode = request.param
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

    disable_interactive_mode = (
        request.config.getoption(name="--disable-interactive-mode") or not interactive_mode
    )
    logger.info("Setting up test-site (interactive-mode=%s) ...", not disable_interactive_mode)
    test_site = _get_site(base_version, interactive=not disable_interactive_mode)
    yield test_site, disable_interactive_mode
    logger.info("Removing test-site...")
    test_site.rm()


def update_site(site: Site, target_version: CMKVersion, interactive_mode: bool) -> Site:
    """Update the test site to the target version."""
    logger.info("Updating site (interactive-mode=%s) ...", interactive_mode)
    return _get_site(target_version, base_site=site, interactive=interactive_mode)


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(test_setup: tuple, tmp_path: Path) -> Path:
    test_site, _ = test_setup
    return download_and_install_agent_package(test_site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state
