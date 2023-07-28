# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator

import pytest

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import execute

from tests.plugins_integration import constants
from tests.plugins_integration.checks import get_host_names

LOGGER = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--update-checks",
        action="store_true",
        default=False,
        help="Store checks-output files to be used as static references",
    )

    parser.addoption(
        "--skip-cleanup",
        action="store_true",
        default=False,
        help="Skip cleanup process after tests' execution",
    )


@pytest.fixture(name="test_site", scope="session")
def get_site() -> Iterator[Site]:
    yield from get_site_factory(prefix="plugins_", update_from_git=False).get_test_site()


@pytest.fixture(scope="session")
def setup(test_site: Site, request: pytest.FixtureRequest) -> Iterator:
    """Setup test-site and perform cleanup after test execution."""
    dump_path = test_site.path(f"var/check_mk/{constants.DUMP_DIR}")

    # create dump folder in the test site
    LOGGER.info('Creating folder "%s"...', dump_path)
    rc = test_site.execute(["mkdir", "-p", dump_path]).wait()
    assert rc == 0

    LOGGER.info("Injecting agent-output...")
    assert execute(["sudo", "cp", "-r", f"{constants.DUMP_DIR_PATH}/.", dump_path]).returncode == 0

    for dump_type in constants.DUMP_TYPES:
        host_folder = f"/{dump_type}"
        if test_site.openapi.get_folder(host_folder):
            LOGGER.info('Host folder "%s" already exists!', host_folder)
        else:
            LOGGER.info('Creating host folder "%s"...', host_folder)
            test_site.openapi.create_folder(host_folder)
        ruleset_name = "usewalk_hosts" if dump_type == "snmp" else "datasource_programs"
        LOGGER.info('Creating rule "%s"...', ruleset_name)
        test_site.openapi.create_rule(
            ruleset_name=ruleset_name,
            value=(True if dump_type == "snmp" else f"cat {dump_path}/<HOST>"),
            folder=host_folder,
        )
        LOGGER.info('Rule "%s" created!', ruleset_name)
        LOGGER.info("Getting host names...")
        host_names = [_ for _ in get_host_names() if ("snmp" in _) == (dump_type == "snmp")]
        LOGGER.info("Creating hosts...")
        host_attributes = {
            "ipaddress": "127.0.0.1",
            "tag_agent": ("cmk-agent" if dump_type == "agent" else "no-agent"),
        }
        if dump_type == "snmp":
            host_attributes["tag_snmp_ds"] = "snmpv2"
        test_site.openapi.bulk_create_hosts(
            [
                {
                    "host_name": host_name,
                    "folder": host_folder,
                    "attributes": host_attributes,
                }
                for host_name in host_names
            ],
            bake_agent=False,
            ignore_existing=True,
        )

    LOGGER.info("Activating changes & reloading core...")
    test_site.activate_changes_and_wait_for_core_reload()

    LOGGER.info("Running update-config...")
    assert test_site.execute(["cmk-update-config"]).wait() == 0

    LOGGER.info("Running service discovery...")
    if os.getenv("CMK_SERVICE_DISCOVERY") == "1":
        assert test_site.execute(["cmk", "-vI"]).wait() == 0
    else:
        test_site.openapi.bulk_discover_services(host_names, bulk_size=10, wait_for_completion=True)

    LOGGER.info("Activating changes & reloading core...")
    test_site.activate_changes_and_wait_for_core_reload()

    LOGGER.info("Checking for pending services...")
    pending_checks = {_: test_site.openapi.get_host_services(_, pending=True) for _ in host_names}
    num_tries = 3
    for _ in range(num_tries):
        for host_name in list(pending_checks.keys())[:]:
            test_site.schedule_check(host_name, "Check_MK", 0, 60)
            pending_checks[host_name] = test_site.openapi.get_host_services(host_name, pending=True)
            if len(pending_checks[host_name]) == 0:
                pending_checks.pop(host_name, None)
                continue

    for host_name in pending_checks:
        LOGGER.info(
            '%s pending service(s) found on host "%s": %s',
            len(pending_checks[host_name]),
            host_name,
            ",".join(
                _.get("extensions", {}).get("description", _.get("id"))
                for _ in pending_checks[host_name]
            ),
        )

    yield

    if not request.config.getoption("--skip-cleanup"):
        # cleanup existing agent-output folder in the test site
        LOGGER.info('Removing folder "%s"...', dump_path)
        assert execute(["sudo", "rm", "-rf", dump_path]).returncode == 0
