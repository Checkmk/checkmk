# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import re
from collections.abc import Iterator

import pytest

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import run

from tests.plugins_integration import checks

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
        "--bulk-mode",
        action="store_true",
        default=False,
        help="Enable bulk mode execution",
    )
    parser.addoption(
        "--chunk-index",
        action="store",
        type=int,
        default=0,
        help="Chunk index for bulk mode",
    )
    parser.addoption(
        "--chunk-size",
        action="store",
        type=int,
        default=100,
        help="Chunk size for bulk mode",
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
        else checks.CheckModes.ADD
        if config.getoption("--add-checks")
        else checks.CheckModes.DEFAULT
    )
    checks.config.skip_masking = config.getoption("--skip-masking")
    checks.config.skip_cleanup = config.getoption("--skip-cleanup")
    checks.config.data_dir = config.getoption(name="--data-dir")
    checks.config.dump_dir = config.getoption(name="--dump-dir")
    checks.config.response_dir = config.getoption(name="--response-dir")
    checks.config.diff_dir = config.getoption(name="--diff-dir")
    checks.config.host_names = config.getoption(name="--host-names")
    checks.config.check_names = config.getoption(name="--check-names")
    checks.config.dump_types = config.getoption(name="--dump-types")

    checks.config.load()


def pytest_collection_modifyitems(config, items):
    """Enable or disable tests based on their bulk mode"""
    if config.getoption(name="--bulk-mode"):
        chunk_index = config.getoption(name="--chunk-index")
        chunk_size = config.getoption(name="--chunk-size")
        items[:] = items[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
        for item in items:
            item.fixturenames.append("bulk_setup")
    print(f"selected {len(items)} items")


@pytest.fixture(name="test_site", scope="session")
def _get_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    skip_cleanup = request.config.getoption("--skip-cleanup")
    for site in get_site_factory(prefix="plugins_").get_test_site(auto_cleanup=not skip_cleanup):
        dump_path = site.path("var/check_mk/dumps")
        # NOTE: the snmpwalks folder cannot be changed!
        walk_path = site.path("var/check_mk/snmpwalks")
        # create dump folder in the test site
        logger.info('Creating folder "%s"...', dump_path)
        rc = site.execute(["mkdir", "-p", dump_path]).wait()
        assert rc == 0

        logger.info("Injecting agent-output...")
        for dump_name in checks.get_host_names():
            assert (
                run(
                    [
                        "sudo",
                        "cp",
                        "-f",
                        f"{checks.config.dump_dir}/{dump_name}",
                        f"{walk_path}/{dump_name}"
                        if re.search(r"\bsnmp\b", dump_name)
                        else f"{dump_path}/{dump_name}",
                    ]
                ).returncode
                == 0
            )

        for dump_type in checks.config.dump_types:  # type: ignore
            host_folder = f"/{dump_type}"
            if site.openapi.get_folder(host_folder):
                logger.info('Host folder "%s" already exists!', host_folder)
            else:
                logger.info('Creating host folder "%s"...', host_folder)
                site.openapi.create_folder(host_folder)
            ruleset_name = "usewalk_hosts" if dump_type == "snmp" else "datasource_programs"
            logger.info('Creating rule "%s"...', ruleset_name)
            site.openapi.create_rule(
                ruleset_name=ruleset_name,
                value=(True if dump_type == "snmp" else f"cat {dump_path}/<HOST>"),
                folder=host_folder,
            )
            logger.info('Rule "%s" created!', ruleset_name)

        yield site

        if not skip_cleanup:
            # cleanup existing agent-output folder in the test site
            logger.info('Removing folder "%s"...', dump_path)
            assert run(["sudo", "rm", "-rf", dump_path]).returncode == 0


@pytest.fixture(name="bulk_setup", scope="session")
def _bulk_setup(test_site: Site, pytestconfig: pytest.Config) -> Iterator:
    """Setup multiple test hosts."""
    logger.info("Running bulk setup...")
    chunk_index = pytestconfig.getoption(name="--chunk-index")
    chunk_size = pytestconfig.getoption(name="--chunk-size")
    host_names = checks.get_host_names()[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
    checks.setup_hosts(test_site, host_names)
    yield
    if os.getenv("CLEANUP", "1") == "1" and not pytestconfig.getoption("--skip-cleanup"):
        checks.cleanup_hosts(test_site, host_names)
