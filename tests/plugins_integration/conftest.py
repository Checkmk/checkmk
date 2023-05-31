# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest

from tests.testlib.openapi_session import UnexpectedResponse
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name, execute

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


def pytest_configure(config):
    config.addinivalue_line("markers", "update_checks: run test marked as update_checks")


def pytest_collection_modifyitems(config, items):
    skip_update_checks = pytest.mark.skip(
        reason="Test used to store checks output. Selectable with --update-checks"
    )
    skip_check_tests = pytest.mark.skip(
        reason="Only tests marked as 'update_checks' have been selected"
    )
    for item in items:
        if ("update_checks" in item.keywords) == config.getoption("--update-checks"):
            continue
        item.add_marker(
            skip_update_checks if "update_checks" in item.keywords else skip_check_tests
        )


@pytest.fixture(name="test_site", scope="session")
def get_site() -> Generator:
    LOGGER.info("Setting up testsite")
    reuse = os.environ.get("REUSE")
    # if REUSE is undefined, a site will neither be reused nor be dropped
    reuse_site = reuse == "1"
    drop_site = reuse == "0"
    sf = get_site_factory(
        prefix="plugins_",
        fallback_branch=current_base_branch_name,
    )

    site_to_return = sf.get_existing_site("central")
    if site_to_return.exists() and reuse_site:
        LOGGER.info("Reuse existing site (REUSE=1)")
    else:
        if site_to_return.exists() and drop_site:
            LOGGER.info("Dropping existing site (REUSE=0)")
            site_to_return.rm()
        LOGGER.info("Creating new site")
        site_to_return = sf.get_site("central")
    LOGGER.info("Testsite %s is up", site_to_return.id)

    try:
        yield site_to_return
    finally:
        # teardown: saving results
        site_to_return.save_results()


@pytest.fixture(scope="session")
def setup(test_site: Site, request: pytest.FixtureRequest) -> Generator:
    """Setup test-site and perform cleanup after test execution."""

    agent_output_path = test_site.path("var/check_mk/agent_output")

    # create agent-output folders in the test site
    LOGGER.info('Creating folder "%s"...', agent_output_path)
    rc = test_site.execute(["mkdir", "-p", agent_output_path]).wait()
    assert rc == 0

    injected_output = str(Path(__file__).parent.resolve() / "agent_output")
    host_folder = "/agents"

    LOGGER.info("Injecting agent-output...")
    assert execute(["sudo", "cp", "-r", f"{injected_output}/.", agent_output_path]).returncode == 0

    try:
        test_site.openapi.get_folder(host_folder)
    except UnexpectedResponse as e:
        if not str(e).startswith("[404]"):
            raise e
        test_site.openapi.create_folder(host_folder)
    test_site.openapi.create_rule(
        ruleset_name="datasource_programs",
        value=f"cat {agent_output_path}/<HOST>",
        folder=host_folder,
    )
    hosts = [
        _
        for _ in test_site.check_output(["ls", "-1", agent_output_path]).split("\n")
        if _ and not _.startswith(".")
    ]
    for host in hosts:
        try:
            test_site.openapi.get_host(host)
        except UnexpectedResponse as e:
            if not str(e).startswith("[404]"):
                raise e
            test_site.openapi.create_host(
                host,
                folder=host_folder,
                attributes={"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"},
                bake_agent=False,
            )
        test_site.openapi.discover_services_and_wait_for_completion(host)
    test_site.activate_changes_and_wait_for_core_reload()

    for host in hosts:
        LOGGER.info("Checking for pending services on host %s...", host)
        pending_checks = test_site.openapi.get_host_services(host, pending=True)
        while len(pending_checks) > 0:
            LOGGER.info(
                "The following pending services were found on host %s: %s. Rescheduling checks...",
                host,
                ",".join([_.get("extensions", {}).get("description") for _ in pending_checks]),
            )
            for check in pending_checks:
                try:
                    test_site.schedule_check(
                        host, check.get("extensions", {}).get("description"), 0
                    )
                except AssertionError:
                    pass
            pending_checks = test_site.openapi.get_host_services(host, pending=True)

    yield

    if not request.config.getoption("--skip-cleanup"):
        # cleanup existing agent-output folder in the test site
        LOGGER.info('Removing folder "%s"...', agent_output_path)
        rc = test_site.execute(["rm", "-rf", agent_output_path]).wait()
        assert rc == 0
