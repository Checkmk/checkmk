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

from tests.testlib.licensing import license_site
from tests.testlib.repo import repo_path
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import edition_from_env, parse_raw_edition, run
from tests.testlib.version import CMKVersion, get_min_version, version_from_env

from cmk.ccc.version import Edition

from cmk.utils.licensing.helper import get_licensed_state_file_path
from cmk.utils.paths import omd_root

LOGGER = logging.getLogger(__name__)
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
    parser.addoption(
        "--target-edition",
        action="store",
        default=None,
        help="Edition for the target test-site; Options: CRE, CEE, CCE, CSE, CME.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "cee: marks tests using an enterprise-edition site")
    config.addinivalue_line("markers", "cce: marks tests using a cloud-edition site")
    config.addinivalue_line("markers", "cse: marks tests using a saas-edition site")


@dataclasses.dataclass
class BaseVersions:
    """Get all base versions used for the test."""

    with open(Path(__file__).parent.resolve() / "base_versions.json") as f:
        BASE_VERSIONS_STR = json.load(f)

    if version_from_env().is_saas_edition():
        BASE_VERSIONS = [
            CMKVersion(CMKVersion.DAILY, edition_from_env(Edition.CSE), "2.3.0", "2.3.0")
        ]
    else:
        BASE_VERSIONS = [
            CMKVersion(base_version_str, edition_from_env(Edition.CEE))
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


def _get_omd_status(site: Site) -> dict[str, str]:
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
    service_status = _get_omd_status(site)
    LOGGER.debug("Status codes: %s", service_status)
    if len(service_status) > 0:
        status = list(service_status.values())[-1]
        if status == "partially running":
            return status
        if status in ("running", "stopped") and all(
            value == status for value in service_status.values()
        ):
            return status
        LOGGER.error("Invalid service status: %s", service_status)
    return None


def _get_site_factory(version: CMKVersion) -> SiteFactory:
    return SiteFactory(
        version=CMKVersion(version.version, version.edition),
        prefix="update_",
        enforce_english_gui=False,
    )


def _create_site(base_version: CMKVersion) -> Site:
    site_name = "central"
    site_factory = _get_site_factory(base_version)
    site = site_factory.get_existing_site(site_name)
    LOGGER.info("Site exists: %s", site.exists())
    if site.exists():
        LOGGER.info("Dropping existing site ...")
        site.rm()
    elif site.is_running():
        LOGGER.info("Stopping running site before update ...")
        site.stop()
        assert get_site_status(site) == "stopped"
    assert not site.exists(), "Trying to install existing site!"
    LOGGER.info("Creating new site")

    try:
        site = site_factory.get_site(site_name, auto_restart_httpd=True)
    except Exception as e:
        if f"Version {base_version.version} could not be installed" in str(e):
            pytest.skip(
                f"Base-version {base_version.version} not available in "
                f'{os.environ.get("DISTRO")}'
            )
        else:
            raise

    return site


def update_site(base_site: Site, target_version: CMKVersion, interactive: bool) -> Site:
    site_factory = _get_site_factory(target_version)
    min_version = get_min_version(base_site.version.edition)
    LOGGER.info("Updating test-site (interactive-mode=%s) ...", interactive)
    if interactive:
        target_site = site_factory.interactive_update(
            base_site,
            target_version=target_version,
            min_version=min_version,
            timeout=60,
        )
    else:
        target_site = site_factory.update_as_site_user(
            base_site, target_version=target_version, min_version=min_version
        )

    return target_site


def _get_rel_path(full_path: Path) -> Path:
    # NOTE: omd_root is always truthy because it's a Path
    return full_path.relative_to(omd_root)


def is_test_site_licensed(test_site: Site) -> bool:
    return bool(int(test_site.read_file(_get_rel_path(get_licensed_state_file_path()))))


@pytest.fixture(name="test_setup", params=TestParams.TEST_PARAMS, scope="module")
def _setup(request: pytest.FixtureRequest) -> Generator[tuple, None, None]:
    """Install the test site with the base version."""
    base_version, interactive_mode = request.param

    target_edition_raw = request.config.getoption(name="--target-edition")
    target_edition = (
        parse_raw_edition(target_edition_raw)
        if target_edition_raw
        else edition_from_env(Edition.CEE)
    )
    LOGGER.info("Base edition: %s", base_version.edition.short)
    LOGGER.info("Target edition: %s", target_edition.short)

    if (
        request.config.getoption(name="--latest-base-version")
        and base_version.version != BaseVersions.BASE_VERSIONS[-1].version
    ):
        pytest.skip("Only latest base-version selected")

    interactive_mode = interactive_mode and not request.config.getoption(
        name="--disable-interactive-mode"
    )
    LOGGER.info("Setting up test-site ...")
    test_site = _create_site(base_version)

    inject_dumps(test_site, DUMPS_DIR)

    disable_rules_injection = request.config.getoption(name="--disable-rules-injection")
    if not version_from_env().is_saas_edition():
        if not disable_rules_injection:
            inject_rules(test_site)

    with license_site(test_site, target_edition):
        test_site.activate_changes_and_wait_for_core_reload()
        assert is_test_site_licensed(test_site)
        yield test_site, target_edition, interactive_mode

    LOGGER.info("Removing test-site...")
    test_site.rm()


def inject_dumps(site: Site, dumps_dir: Path) -> None:
    _dumps_up_to_date(dumps_dir, get_min_version())

    # create dump folder in the test site
    site_dumps_path = site.path("var/check_mk/dumps")
    LOGGER.info('Creating folder "%s"...', site_dumps_path)
    rc = site.execute(["mkdir", "-p", site_dumps_path]).wait()
    assert rc == 0

    LOGGER.info("Injecting agent-output...")

    for dump_name in list(os.listdir(dumps_dir)):
        assert (
            run(
                [
                    "cp",
                    "-f",
                    f"{dumps_dir}/{dump_name}",
                    f"{site_dumps_path}/{dump_name}",
                ],
                sudo=True,
            ).returncode
            == 0
        )

    ruleset_name = "datasource_programs"
    LOGGER.info('Creating rule "%s"...', ruleset_name)
    site.openapi.create_rule(ruleset_name=ruleset_name, value=f"cat {site_dumps_path}/*")
    LOGGER.info('Rule "%s" created!', ruleset_name)


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
            LOGGER.info('Importing rules file "%s"...', rules_file_path)
            rules = json.load(ruleset_file)
            for rule in rules:
                site.openapi.create_rule(value=rule)
    site.activate_changes_and_wait_for_core_reload()


def _dumps_up_to_date(dumps_dir: Path, min_version: CMKVersion) -> None:
    """Check if the dumps are up-to-date with the minimum-version branch."""
    dumps = list(dumps_dir.glob("*"))
    min_version_str = min_version.version
    min_version_branch = min_version_str[: min_version_str.find("p")]
    if not dumps:
        raise FileNotFoundError("No dumps found!")
    for dump in dumps:
        if str(min_version_branch) not in dump.name:
            raise ValueError(
                f"Dump '{dump.name}' is outdated! "
                f"Please regenerate it using an agent with version {min_version_branch}."
            )
