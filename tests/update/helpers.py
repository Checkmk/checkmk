#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import (
    get_services_with_status,
    get_supported_distros,
    parse_files,
    ServiceInfo,
    version_spec_from_env,
)
from tests.testlib.version import (
    CMKEdition,
    CMKPackageInfo,
    CMKVersion,
    edition_from_env,
    get_min_version,
    TypeCMKEdition,
)

MODULE_PATH = Path(__file__).parent.resolve()
RULES_DIR = MODULE_PATH / "rules"
DUMPS_DIR = MODULE_PATH / "dumps"

logger = logging.getLogger(__name__)


def _get_omd_status(site: Site) -> dict[str, str]:
    """Get the omd status for all services of the given site."""
    cmd = [site.path("bin/omd").as_posix(), "status", "--bare"]
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
    service_status = _get_omd_status(site)
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


def _get_site_factory(package: CMKPackageInfo) -> SiteFactory:
    return SiteFactory(
        package=package,
        prefix="update_",
        enforce_english_gui=False,
    )


def create_site(base_package: CMKPackageInfo) -> Site:
    site_name = "central"
    site_factory = _get_site_factory(base_package)
    site = site_factory.get_existing_site(site_name)
    logger.info("Site exists: %s", site.exists())
    if site.exists():
        logger.info("Dropping existing site ...")
        site.rm()
    elif site.is_running():
        logger.info("Stopping running site before update ...")
        site.stop()
        assert get_site_status(site) == "stopped"
    assert not site.exists(), "Trying to install existing site!"
    logger.info("Creating new site")

    try:
        site = site_factory.get_site(site_name)
        site_factory.initialize_site(site, auto_restart_httpd=True)
    except FileNotFoundError:
        pytest.skip(
            f"Base-version '{base_package.version.version}' is not available for distro "
            f"{os.environ.get('DISTRO')}"
        )

    return site


def get_target_package(target_edition: TypeCMKEdition) -> CMKPackageInfo:
    return CMKPackageInfo(CMKVersion(version_spec_from_env(CMKVersion.DAILY)), target_edition)


def update_site(base_site: Site, target_package: CMKPackageInfo, interactive: bool) -> Site:
    site_factory = _get_site_factory(target_package)
    min_version = get_min_version()
    logger.info("Updating test-site (interactive-mode=%s) ...", interactive)
    if interactive:
        target_site = site_factory.interactive_update(
            base_site,
            target_package,
            min_version=min_version,
            timeout=60,
        )
    else:
        target_site = site_factory.update_as_site_user(
            base_site, target_package, min_version=min_version
        )

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.debug("Successfully updated '%s' > '%s'!", base_site.package, target_site.package)

    assert str(target_package) in target_site.check_output(["omd", "version"]), (
        "Edition and/or version mismatch during update!"
    )

    return target_site


def create_password(site: Site) -> None:
    site.openapi.passwords.create(
        ident="mydummypass",
        title="Dummypass",
        comment="",
        password="dummy",
        owner="admin",
    )
    site.openapi.changes.activate_and_wait_for_completion()


def inject_rules(site: Site) -> None:
    try:
        with open(RULES_DIR / "ignore.txt", encoding="UTF-8") as ignore_list_file:
            ignore_list = [_ for _ in ignore_list_file.read().splitlines() if _]
    except FileNotFoundError:
        ignore_list = []
    rules_file_names = [
        _ for _ in os.listdir(RULES_DIR) if _.endswith(".json") and _ not in ignore_list
    ]
    for rules_file_name in rules_file_names:
        if edition_from_env().is_raw_edition() and rules_file_name.startswith("cmc_"):
            continue
        rules_file_path = RULES_DIR / rules_file_name
        with open(rules_file_path, encoding="UTF-8") as ruleset_file:
            logger.info('Importing rules file "%s"...', rules_file_path)
            rules = json.load(ruleset_file)
            for rule in rules:
                site.openapi.rules.create(value=rule)
    site.activate_changes_and_wait_for_core_reload()


def cleanup_cmk_package(site: Site, request: pytest.FixtureRequest) -> None:
    if os.getenv("CLEANUP", "1") == "1" and not request.config.getoption(name="--skip-uninstall"):
        site.uninstall_cmk()


def check_agent_receiver_error_log(site: Site) -> None:
    """Assert that there are no unexpected errors in the agent receiver log."""
    error_match_dict = parse_files(pathname=site.logs_dir / "**/*log*", pattern="error")

    # TODO: Remove the following block after CMK-18520 is done
    agent_receiver_error_log = str(site.logs_dir / "agent-receiver/error.log")
    if agent_receiver_error_log in error_match_dict:
        error_match_dict.pop(agent_receiver_error_log)

    assert not error_match_dict, f"Error string found in one or more log files: {error_match_dict}"


def check_services(site: Site, hostname: str, base_data: dict[str, ServiceInfo]) -> None:
    """Assert that current service status matches previous service status."""
    # get update monitoring data
    target_data = site.get_host_services(hostname)

    base_ok_services = get_services_with_status(base_data, 0)
    target_ok_services = get_services_with_status(target_data, 0)

    not_found_services = [service for service in base_data if service not in target_data]
    err_msg = (
        f"The following services were found in base-version but not in target-version: "
        f"{not_found_services}"
    )
    assert len(target_data) >= len(base_data), err_msg

    not_ok_services = [service for service in base_ok_services if service not in target_ok_services]
    err_details = [
        (s, "state: " + str(target_data[s].state), target_data[s].summary) for s in not_ok_services
    ]
    err_msg = (
        f"The following services were `OK` in base-version but not in target-version: "
        f"{not_ok_services}"
        f"\nDetails: {err_details})"
    )
    assert base_ok_services.issubset(target_ok_services), err_msg


def check_core_reinit(site: Site) -> None:
    """reinitialize (reload, then restart) the core and check the output"""

    # reload the core and check the output (see CMK-20653)
    logger.info("Reloading the core...")
    ret_reload = site.run(["cmk", "--reload", "--debug"])
    assert ret_reload.returncode == 0 and not ret_reload.stderr, "Reloading the core failed!"
    assert get_site_status(site) == "running", "Invalid service status after reloading!"

    # restart the core and check the output (see CMK-20653)
    logger.info("Restarting the core...")
    ret_restart = site.run(["cmk", "--restart", "--debug"])
    assert ret_restart.returncode == 0 and not ret_restart.stderr, "Restarting the core failed!"
    assert get_site_status(site) == "running", "Invalid service status after restarting!"


def bulk_discover_and_schedule(site: Site, hostname: str) -> None:
    """Run service bulk discovery for a single host (ignoring errors), activate changes and schedule checks."""
    logger.debug("Discovering services and waiting for completion...")
    site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion([hostname])
    site.openapi.changes.activate_and_wait_for_completion()
    site.schedule_check(hostname, "Check_MK", 0)


@dataclass
class BaseVersions:
    """Get all base versions used for the test. Up to five versions are used per branch:
    The first one and the last four.
    """

    @staticmethod
    def _limit_versions(versions: list[str], min_version: CMKVersion) -> list[str]:
        """Select supported earliest and latest versions and eliminate duplicates"""
        max_earliest_versions = 1
        max_latest_versions = 4

        active_versions = [_ for _ in versions if CMKVersion(_) >= min_version]
        earliest_versions = active_versions[0:max_earliest_versions]
        latest_versions = active_versions[-max_latest_versions:]
        # do not use a set to retain the order
        return list(dict.fromkeys(earliest_versions + latest_versions))

    min_version = get_min_version()

    if edition_from_env().is_saas_edition():
        base_packages = [
            CMKPackageInfo(
                CMKVersion(CMKVersion.DAILY, "2.4.0", "2.4.0"), CMKEdition(CMKEdition.CSE)
            )
        ]
    else:
        base_versions_pb_file = MODULE_PATH / "base_versions_previous_branch.json"
        if not base_versions_pb_file.exists():
            base_versions_pb_file = MODULE_PATH / "base_versions.json"
        base_versions_pb = _limit_versions(
            json.loads(base_versions_pb_file.read_text(encoding="utf-8")), min_version
        )

        base_versions_cb_file = MODULE_PATH / "base_versions_current_branch.json"
        base_versions_cb = (
            _limit_versions(
                json.loads(base_versions_cb_file.read_text(encoding="utf-8")),
                min_version,
            )
            if base_versions_cb_file.exists()
            else []
        )

        base_packages = [
            CMKPackageInfo(CMKVersion(base_version_str), edition_from_env())
            for base_version_str in base_versions_pb + base_versions_cb
        ]


@dataclass
class InteractiveModeDistros:
    DISTROS = ["ubuntu-22.04", "almalinux-9"]
    assert set(DISTROS).issubset(set(get_supported_distros()))


@dataclass
class TestParams:
    """Pytest parameters used in the test."""

    INTERACTIVE_MODE = [True, False]
    TEST_PARAMS = [
        pytest.param(
            (base_package, interactive_mode),
            id=f"base-version={base_package.version.version}|interactive-mode={interactive_mode}",
        )
        for base_package, interactive_mode in itertools.product(
            BaseVersions.base_packages, INTERACTIVE_MODE
        )
        # interactive mode enabled for some specific distros
        if interactive_mode == (os.environ.get("DISTRO") in InteractiveModeDistros.DISTROS)
    ]
