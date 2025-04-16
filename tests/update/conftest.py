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
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from tests.testlib.agent_dumps import inject_dumps
from tests.testlib.repo import repo_path
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import edition_from_env, restart_httpd
from tests.testlib.version import CMKVersion, get_min_version

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)
MODULE_DIR = Path(__file__).parent.resolve()
DUMPS_DIR = MODULE_DIR / "dumps"


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
    config.addinivalue_line("markers", "cse: marks tests using a saas-edition site")


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test. Up to five versions are used per branch:
    The first one and the last four.
    """

    @staticmethod
    def _limit_versions(versions: list[str], min_version: CMKVersion) -> list[str]:
        """Select supported earliest and latest versions and eliminate duplicates"""
        max_earliest_versions = 1
        max_latest_versions = 4

        active_versions = [_ for _ in versions if CMKVersion(_, min_version.edition) >= min_version]
        earliest_versions = active_versions[0:max_earliest_versions]
        latest_versions = active_versions[-max_latest_versions:]
        # do not use a set to retain the order
        return list(dict.fromkeys(earliest_versions + latest_versions))

    MIN_VERSION = get_min_version()

    previous_branch_versions_file = MODULE_DIR / "base_versions_previous_branch.json"
    BASE_VERSIONS_PB = _limit_versions(
        json.loads(previous_branch_versions_file.read_text(encoding="utf-8")),
        MIN_VERSION,
    )

    current_branch_versions_file = MODULE_DIR / "base_versions_current_branch.json"
    try:
        BASE_VERSIONS_CB = _limit_versions(
            json.loads(current_branch_versions_file.read_text(encoding="utf-8")),
            MIN_VERSION,
        )
    except FileNotFoundError:
        BASE_VERSIONS_CB = []

    BASE_VERSIONS = [
        CMKVersion(base_version_str, edition_from_env(fallback=Edition.CEE))
        for base_version_str in BASE_VERSIONS_PB + BASE_VERSIONS_CB
    ]


@dataclasses.dataclass
class InteractiveModeDistros:
    @staticmethod
    def get_supported_distros():
        with open(repo_path() / "editions.yml", "r") as stream:
            yaml_file = yaml.safe_load(stream)

        return yaml_file["common"]

    DISTROS = ["ubuntu-22.04", "almalinux-9"]
    assert set(DISTROS).issubset(set(get_supported_distros()))


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
        if interactive_mode == (os.environ.get("DISTRO") in InteractiveModeDistros.DISTROS)
    ]


def get_omd_status(site: Site) -> dict[str, str]:
    """Get the omd status for all services of the given site."""
    cmd = [site.path("bin/omd"), "status", "--bare"]
    status = {}
    process = site.execute(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        logger.error("omd status returned RC%s and STDERR=%s", process.returncode, stderr)
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


def _get_site(  # pylint: disable=too-many-branches
    version: CMKVersion, interactive: bool, base_site: Site | None = None
) -> Site:
    """Install or update the test site with the given version.

    An update installation is done automatically when an optional base_site is given.
    By default, both installing and updating is done directly via spawn_expect_process()."""
    update = base_site is not None and base_site.exists()
    update_conflict_mode = "keepold"
    min_version = BaseVersions.MIN_VERSION
    sf = SiteFactory(
        version=CMKVersion(version.version, version.edition),
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
                timeout=60,
            )
        else:  # interactive site creation
            try:
                site = sf.interactive_create(site.id, logfile_path, timeout=60)
                restart_httpd()
            except Exception as e:
                if f"Version {version.version} could not be installed" in str(e):
                    pytest.skip(
                        f"Base-version {version.version} not available in "
                        f'{os.environ.get("DISTRO")}'
                    )
                else:
                    raise
    elif update:
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
            else:
                raise

    return site


@pytest.fixture(name="test_setup", params=TestParams.TEST_PARAMS, scope="module")
def _setup(request: pytest.FixtureRequest) -> Generator[tuple, None, None]:
    """Install the test site with the base version."""
    base_version, interactive_mode = request.param
    if (
        request.config.getoption(name="--latest-base-version")
        and base_version.version != BaseVersions.BASE_VERSIONS[-1].version
    ):
        pytest.skip("Only latest base-version selected")

    disable_interactive_mode = (
        request.config.getoption(name="--disable-interactive-mode") or not interactive_mode
    )
    logger.info("Setting up test-site (interactive-mode=%s) ...", not disable_interactive_mode)
    test_site = _get_site(base_version, interactive=not disable_interactive_mode)
    inject_dumps(test_site, DUMPS_DIR)
    yield test_site, disable_interactive_mode
    logger.info("Removing test-site...")
    test_site.rm()


def update_site(site: Site, target_version: CMKVersion, interactive_mode: bool) -> Site:
    """Update the test site to the target version."""
    logger.info("Updating site (interactive-mode=%s) ...", interactive_mode)
    return _get_site(target_version, base_site=site, interactive=interactive_mode)
