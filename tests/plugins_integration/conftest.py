#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

import pytest

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site, SiteFactory
from tests.testlib.utils import run
from tests.testlib.version import CMKEdition, CMKPackageInfo, get_min_version

from tests.plugins_integration import checks

logger = logging.getLogger(__name__)
cleanup: Final[bool] = os.getenv("CLEANUP", "1") == "1"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-checks",
        action="store_true",
        default=False,
        help="Store updated check output as static references: checks already stored as reference"
        "are updated and new ones are added.",
    )
    parser.addoption(
        "--add-checks",
        action="store_true",
        default=False,
        help="Store added check output as static references: checks already stored as reference are"
        "not touched. Only new checks are added.",
    )
    parser.addoption(
        "--skip-cleanup",
        action="store_true",
        default=os.getenv("CLEANUP", "1") != "1",
        help="Skip cleanup process after test execution",
    )
    parser.addoption(
        "--check-names",
        action="store",
        nargs="+",
        help="Check name allow list",
        default=None,
    )
    parser.addoption(
        "--data-dir",
        action="store",
        type=Path,
        help="Data dir path",
        default=None,
    )
    parser.addoption(
        "--dump-dir",
        action="store",
        type=Path,
        help="Dump dir path",
        default=None,
    )
    parser.addoption(
        "--response-dir",
        action="store",
        type=Path,
        help="Response dir path",
        default=None,
    )
    parser.addoption(
        "--diff-dir",
        action="store",
        type=Path,
        help="Diff dir path",
        default=None,
    )


def pytest_configure(config: pytest.Config) -> None:
    # parse options that control the test execution
    checks.config = checks.CheckConfig(
        mode=(
            checks.CheckModes.UPDATE
            if config.getoption("--update-checks")
            else (
                checks.CheckModes.ADD
                if config.getoption("--add-checks")
                else checks.CheckModes.DEFAULT
            )
        ),
        skip_cleanup=_skip_cleanup_option
        if isinstance(_skip_cleanup_option := config.getoption("--skip-cleanup"), bool)
        else False,
        data_dir_integration=_data_dir_option
        if isinstance(_data_dir_option := config.getoption(name="--data-dir"), Path)
        else None,
        dump_dir_integration=_dump_dir_option
        if isinstance(_dump_dir_option := config.getoption(name="--dump-dir"), Path)
        else None,
        response_dir_integration=_response_dir_option
        if isinstance(_response_dir_option := config.getoption(name="--response-dir"), Path)
        else None,
        diff_dir=_ if isinstance(_ := config.getoption(name="--diff-dir"), Path) else None,
        check_names=_ if isinstance(_ := config.getoption(name="--check-names"), list) else None,
    )


@pytest.fixture(name="test_site", scope="session")
def _get_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        for site in get_site_factory(prefix="plugins_").get_test_site(
            auto_cleanup=not checks.config.skip_cleanup
        ):
            dump_path = site.path("var/check_mk/dumps")
            checks.setup_site(site, dump_path)

            yield site

            if not checks.config.skip_cleanup:
                # cleanup existing agent-output folder in the test site
                logger.info('Removing folder "%s"...', dump_path)
                assert run(["rm", "-rf", dump_path.as_posix()], sudo=True).returncode == 0


@pytest.fixture(name="test_site_piggyback", scope="session")
def _get_site_piggyback(request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        for site in get_site_factory(prefix="PB_").get_test_site(
            auto_cleanup=not checks.config.skip_cleanup
        ):
            with _modify_dcd_global_settings(site), _setup_datasource(site):
                yield site


@contextmanager
def _modify_dcd_global_settings(site: Site) -> Iterator[None]:
    """Set global settings for dynamic configuration

    High timeout values to make DCD being only triggered manually within the test execution.
    """
    wato_dir = site.path("etc/check_mk/dcd.d/wato")
    logger.info("Setting dynamic configuration global settings...")
    try:
        site.run(["cp", str(wato_dir / "global.mk"), str(wato_dir / "global.mk.bak")])
        site.write_file(
            "etc/check_mk/dcd.d/wato/global.mk",
            "dcd_activate_changes_timeout = 3600\n"
            "dcd_bulk_discovery_timeout = 3600\n"
            "dcd_site_update_interval = 3600\n",
        )
        yield
    finally:
        if cleanup:
            # restore original global settings
            site.run(["cp", str(wato_dir / "global.mk.bak"), str(wato_dir / "global.mk")])
            logger.info("Restored original global settings in '%s'", wato_dir / "global.mk")
            site.run(["rm", "-f", str(wato_dir / "global.mk.bak")])


@contextmanager
def _setup_datasource(site: Site) -> Iterator[None]:
    """Setup and teardown the datasource rule and the dump directory for the test site."""
    dump_path = site.path("var/check_mk/dumps")
    rule_id = None
    try:
        # create dump folder in the test site
        logger.info('Creating folder "%s"...', dump_path)
        site.run(["mkdir", "-p", dump_path.as_posix()])

        ruleset_name = "datasource_programs"
        logger.info('Creating rule "%s"...', ruleset_name)
        rule_id = site.openapi.rules.create(
            ruleset_name=ruleset_name, value=f"cat {dump_path}/<HOST>"
        )
        logger.info('Rule "%s" created!', ruleset_name)
        yield
    finally:
        if cleanup:
            if rule_id:
                site.openapi.rules.delete(rule_id)
            site.run(["rm", "-rf", dump_path.as_posix()])
            site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(name="site_factory_update", scope="session")
def _get_sf_update():
    base_package = CMKPackageInfo(get_min_version(), CMKEdition(CMKEdition.CEE))
    return get_site_factory(prefix="update_", package=base_package)


@pytest.fixture(name="test_site_update", scope="session")
def _get_site_update(
    site_factory_update: SiteFactory, request: pytest.FixtureRequest
) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        for site in site_factory_update.get_test_site(auto_cleanup=not checks.config.skip_cleanup):
            dump_path = site.path("var/check_mk/dumps")
            checks.setup_site(
                site,
                dump_path,
                [
                    checks.config.dump_dir_integration,
                    checks.config.dump_dir_siteless,
                ],
            )

            yield site

            if not checks.config.skip_cleanup:
                # cleanup existing agent-output folder in the test site
                logger.info('Removing folder "%s"...', dump_path)
                assert run(["rm", "-rf", dump_path.as_posix()], sudo=True).returncode == 0


@pytest.fixture(name="plugin_validation_site", scope="session")
def _get_site_validation(request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from get_site_factory(prefix="val_").get_test_site()


def _periodic_service_discovery_rule() -> dict:
    periodic_discovery = {
        "check_interval": 120.0,
        "severity_unmonitored": 2,
        "severity_vanished": 1,
        "severity_changed_service_labels": 1,
        "severity_changed_service_params": 1,
        "severity_new_host_label": 1,
        "inventory_rediscovery": {
            "mode": (
                "custom",
                {
                    "add_new_services": True,
                    "remove_vanished_services": False,
                    "update_changed_service_labels": True,
                    "update_changed_service_parameters": True,
                    "update_host_labels": True,
                },
            ),
            "keep_clustered_vanished_services": True,
            "group_time": 900,
            "excluded_time": [((9, 0), (12, 0))],
            "activation": False,
        },
    }
    return periodic_discovery


@pytest.fixture(name="create_periodic_service_discovery_rule", scope="function")
def _create_periodic_service_discovery_rule(test_site_update: Site) -> Iterator[None]:
    existing_rules_ids = []
    for rule in test_site_update.openapi.rules.get_all("periodic_discovery"):
        existing_rules_ids.append(rule["id"])

    test_site_update.openapi.rules.create(
        ruleset_name="periodic_discovery",
        value=_periodic_service_discovery_rule(),
    )
    test_site_update.openapi.changes.activate_and_wait_for_completion()

    yield

    for rule in test_site_update.openapi.rules.get_all("periodic_discovery"):
        if rule["id"] not in existing_rules_ids:
            test_site_update.openapi.rules.delete(rule["id"])
    test_site_update.openapi.changes.activate_and_wait_for_completion()
