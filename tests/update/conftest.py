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

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import edition_from_env, repo_path, restart_httpd, run
from tests.testlib.version import CMKVersion, get_min_version, version_from_env

logger = logging.getLogger(__name__)
DUMPS_DIR = Path(__file__).parent.resolve() / "dumps"
RULES_DIR = repo_path() / "tests" / "update" / "rules"


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
    parser.addoption(
        "--disable-rules-injection",
        action="store_true",
        default=False,
        help="Disable rules' injection in the test-site.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "cee: marks tests using an enterprise-edition site")
    config.addinivalue_line("markers", "cce: marks tests using a cloud-edition site")
    config.addinivalue_line("markers", "cse: marks tests using a saas-edition site")


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    MIN_VERSION = get_min_version()

    with open(Path(__file__).parent.resolve() / "base_versions.json") as f:
        BASE_VERSIONS_STR = json.load(f)

    if version_from_env().is_saas_edition():
        BASE_VERSIONS = [CMKVersion(CMKVersion.DAILY, edition_from_env(), "2.3.0", "2.3.0")]
    else:
        BASE_VERSIONS = [
            CMKVersion(base_version_str, edition_from_env())
            for base_version_str in BASE_VERSIONS_STR
            if not version_from_env().is_saas_edition()
        ]


@dataclasses.dataclass
class InteractiveModeDistros:
    @staticmethod
    def get_supported_distros():
        with open(Path(__file__).parent.resolve() / "../../editions.yml") as stream:
            yaml_file = yaml.safe_load(stream)

        return yaml_file["daily_extended"]

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


def _get_site(  # pylint: disable=too-many-branches
    version: CMKVersion, interactive: bool, base_site: Site | None = None
) -> Site:
    """Install or update the test site with the given version.

    An update installation is done automatically when an optional base_site is given.
    By default, both installing and updating is done directly via spawn_expect_process().
    """
    prefix = "update_"
    sitename = "central"

    update = base_site is not None and base_site.exists()
    update_conflict_mode = "keepold"
    min_version = BaseVersions.MIN_VERSION
    sf = SiteFactory(
        version=CMKVersion(version.version, version.edition),
        prefix=prefix,
        update=update,
        update_conflict_mode=update_conflict_mode,
        enforce_english_gui=False,
    )
    site = sf.get_existing_site(sitename)

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
            site = sf.get_site(sitename, auto_restart_httpd=True)
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

    disable_rules_injection = request.config.getoption(name="--disable-rules-injection")
    if not version_from_env().is_saas_edition():
        # 'datasource_programs' rule is not supported in the SaaS edition
        inject_dumps(test_site, DUMPS_DIR)
        if not disable_rules_injection:
            inject_rules(test_site)

    yield test_site, disable_interactive_mode
    logger.info("Removing test-site...")
    test_site.rm()


def update_site(site: Site, target_version: CMKVersion, interactive_mode: bool) -> Site:
    """Update the test site to the target version."""
    logger.info("Updating site (interactive-mode=%s) ...", interactive_mode)
    return _get_site(target_version, base_site=site, interactive=interactive_mode)


def inject_dumps(site: Site, dumps_dir: Path) -> None:
    # create dump folder in the test site
    site_dumps_path = site.path("var/check_mk/dumps")
    logger.info('Creating folder "%s"...', site_dumps_path)
    rc = site.execute(["mkdir", "-p", site_dumps_path]).wait()
    assert rc == 0

    logger.info("Injecting agent-output...")

    for dump_name in list(os.listdir(dumps_dir)):
        assert (
            run(
                [
                    "sudo",
                    "cp",
                    "-f",
                    f"{dumps_dir}/{dump_name}",
                    f"{site_dumps_path}/{dump_name}",
                ]
            ).returncode
            == 0
        )

    ruleset_name = "datasource_programs"
    logger.info('Creating rule "%s"...', ruleset_name)
    site.openapi.create_rule(ruleset_name=ruleset_name, value=f"cat {site_dumps_path}/*")
    logger.info('Rule "%s" created!', ruleset_name)


def inject_rules(site: Site) -> None:
    try:
        with open(RULES_DIR / "ignore.txt", "r", encoding="UTF-8") as ignore_list_file:
            ignore_list = [_ for _ in ignore_list_file.read().splitlines() if _]
    except FileNotFoundError:
        ignore_list = []
    rules_file_names = [
        _ for _ in os.listdir(RULES_DIR) if _.endswith(".json") and _ not in ignore_list
    ]
    for rules_file_name in rules_file_names:
        rules_file_path = RULES_DIR / rules_file_name
        with open(rules_file_path, "r", encoding="UTF-8") as ruleset_file:
            logger.info('Importing rules file "%s"...', rules_file_path)
            rules = json.load(ruleset_file)
            for rule in rules:
                site.openapi.create_rule(value=rule)
    site.activate_changes_and_wait_for_core_reload()
