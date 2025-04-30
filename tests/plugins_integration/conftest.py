#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator

import pytest

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site, SiteFactory
from tests.testlib.utils import run
from tests.testlib.version import get_min_version

from tests.plugins_integration import checks

from cmk.ccc.version import Edition

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
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
        "--skip-masking",
        action="store_true",
        default=False,
        help="Skip regexp masking during check validation",
    )
    parser.addoption(
        "--enable-core-scheduling",
        action="store_true",
        default=False,
        help="Enable core scheduling (disabled by default)",
    )
    parser.addoption(
        "--host-names",
        action="store",
        help="Host name allow list",
        default=None,
    )
    parser.addoption(
        "--check-names",
        action="store",
        help="Check name allow list",
        default=None,
    )
    parser.addoption(
        "--data-dir",
        action="store",
        help="Data dir path",
        default=None,
    )
    parser.addoption(
        "--dump-dir",
        action="store",
        help="Dump dir path",
        default=None,
    )
    parser.addoption(
        "--response-dir",
        action="store",
        help="Response dir path",
        default=None,
    )
    parser.addoption(
        "--diff-dir",
        action="store",
        help="Diff dir path",
        default=None,
    )
    parser.addoption(
        "--dump-types",
        action="store",
        help='Selected dump types to process (default: "agent,snmp")',
        default=None,
    )


def pytest_configure(config):
    # parse options that control the test execution
    checks.config.mode = (
        checks.CheckModes.UPDATE
        if config.getoption("--update-checks")
        else (
            checks.CheckModes.ADD if config.getoption("--add-checks") else checks.CheckModes.DEFAULT
        )
    )
    checks.config.skip_cleanup = config.getoption("--skip-cleanup")
    checks.config.data_dir = config.getoption(name="--data-dir")
    checks.config.dump_dir = config.getoption(name="--dump-dir")
    checks.config.response_dir = config.getoption(name="--response-dir")
    checks.config.diff_dir = config.getoption(name="--diff-dir")
    checks.config.host_names = config.getoption(name="--host-names")
    checks.config.check_names = config.getoption(name="--check-names")
    checks.config.dump_types = config.getoption(name="--dump-types")

    checks.config.load()


@pytest.fixture(name="test_site", scope="session")
def _get_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        for site in get_site_factory(prefix="plugins_").get_test_site(
            auto_cleanup=not checks.config.skip_cleanup
        ):
            dump_path = site.path("var/check_mk/dumps").as_posix()
            checks.setup_site(site, dump_path)

            yield site

            if not request.config.getoption("--enable-core-scheduling"):
                site.stop_host_checks()
                site.stop_active_services()

            if not checks.config.skip_cleanup:
                # cleanup existing agent-output folder in the test site
                logger.info('Removing folder "%s"...', dump_path)
                assert run(["rm", "-rf", dump_path], sudo=True).returncode == 0


@pytest.fixture(name="test_site_piggyback", scope="session")
def _get_site_piggyback(request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        for site in get_site_factory(prefix="PB_").get_test_site(
            auto_cleanup=not checks.config.skip_cleanup
        ):
            dump_path = site.path("var/check_mk/dumps").as_posix()

            # create dump folder in the test site
            logger.info('Creating folder "%s"...', dump_path)
            _ = site.run(["mkdir", "-p", dump_path])

            ruleset_name = "datasource_programs"
            logger.info('Creating rule "%s"...', ruleset_name)
            site.openapi.rules.create(ruleset_name=ruleset_name, value=f"cat {dump_path}/<HOST>")
            logger.info('Rule "%s" created!', ruleset_name)

            logger.info("Setting dynamic configuration global settings...")
            site.write_text_file(
                "etc/check_mk/dcd.d/wato/global.mk",
                "dcd_activate_changes_timeout = 30\n"
                "dcd_bulk_discovery_timeout = 30\n"
                "dcd_site_update_interval = 60\n",
            )

            yield site


@pytest.fixture(name="site_factory_update", scope="session")
def _get_sf_update():
    base_version = get_min_version(Edition.CEE)
    return get_site_factory(prefix="update_", version=base_version)


@pytest.fixture(name="test_site_update", scope="session")
def _get_site_update(
    site_factory_update: SiteFactory, request: pytest.FixtureRequest
) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        for site in site_factory_update.get_test_site(auto_cleanup=not checks.config.skip_cleanup):
            dump_path = site.path("var/check_mk/dumps").as_posix()
            checks.setup_site(site, dump_path)

            yield site

            if not checks.config.skip_cleanup:
                # cleanup existing agent-output folder in the test site
                logger.info('Removing folder "%s"...', dump_path)
                assert run(["rm", "-rf", dump_path], sudo=True).returncode == 0


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
        "severity_new_host_label": 1,
        "inventory_rediscovery": {
            "mode": (
                "custom",
                {
                    "add_new_services": True,
                    "remove_vanished_services": False,
                    "update_changed_service_labels": True,
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
    test_site_update.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
