# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import re
from collections.abc import Iterator

import pytest

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import execute

from tests.plugins_integration import checks

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--update-checks",
        action="store_true",
        default=False,
        help="Store updated check output as static references",
    )
    parser.addoption(
        "--add-checks",
        action="store_true",
        default=False,
        help="Store added check output as static references",
    )
    parser.addoption(
        "--skip-cleanup",
        action="store_true",
        default=False,
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
    )
    parser.addoption(
        "--check-names",
        action="store",
        help="Check name allow list",
    )
    parser.addoption(
        "--data-dir",
        action="store",
        help="Data dir path",
    )
    parser.addoption(
        "--dump-dir",
        action="store",
        help="Dump dir path",
    )
    parser.addoption(
        "--response-dir",
        action="store",
        help="Response dir path",
    )
    parser.addoption(
        "--dump-types",
        action="store",
        help='Selected dump types to process (default: "agent,snmp")',
    )


def pytest_configure(config):
    # parse options that control the test execution
    if data_dir := config.getoption(name="--data-dir"):
        checks.DATA_DIR = data_dir
        checks.DUMP_DIR = f"{data_dir}/dumps"
        checks.RESPONSE_DIR = f"{data_dir}/responses"
    logger.info("DATA_DIR=%s", checks.DATA_DIR)
    if dump_dir := config.getoption(name="--dump-dir"):
        checks.DUMP_DIR = dump_dir
    logger.info("DUMP_DIR=%s", checks.DUMP_DIR)
    if response_dir := config.getoption(name="--response-dir"):
        checks.RESPONSE_DIR = response_dir
    logger.info("RESPONSE_DIR=%s", checks.RESPONSE_DIR)
    if host_names := config.getoption(name="--host-names"):
        checks.HOST_NAMES = host_names.split(",")
    logger.info("HOST_NAMES=%s", ",".join(checks.HOST_NAMES) if checks.HOST_NAMES else "*")
    if check_names := config.getoption(name="--check-names"):
        checks.CHECK_NAMES = check_names.split(",")
    logger.info("CHECK_NAMES=%s", ",".join(checks.CHECK_NAMES) if checks.CHECK_NAMES else "*")
    if dump_types := config.getoption(name="--dump-types"):
        checks.DUMP_TYPES = dump_types.split(",")
    logger.info("DUMP_TYPES=%s", ",".join(checks.DUMP_TYPES) if checks.DUMP_TYPES else "*")


def pytest_collection_modifyitems(config, items):
    """Enable or disable tests based on their bulk mode"""
    BULK_MODE = config.getoption(name="--bulk-mode")
    items[:] = [_ for _ in items if _.name.startswith("test_bulk") == BULK_MODE]
    if BULK_MODE:
        chunk_index = config.getoption(name="--chunk-index")
        chunk_size = config.getoption(name="--chunk-size")
        items[:] = items[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
    print(f"selected {len(items)} items")


@pytest.fixture(name="test_site", scope="session")
def _get_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    for site in get_site_factory(prefix="plugins_").get_test_site():
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
                execute(
                    [
                        "sudo",
                        "cp",
                        "-f",
                        f"{checks.DUMP_DIR}/{dump_name}",
                        f"{walk_path}/{dump_name}"
                        if re.search(r"\bsnmp\b", dump_name)
                        else f"{dump_path}/{dump_name}",
                    ]
                ).returncode
                == 0
            )

        for dump_type in checks.DUMP_TYPES:
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

        if os.getenv("CLEANUP", "1") == "1" and not request.config.getoption("--skip-cleanup"):
            # cleanup existing agent-output folder in the test site
            logger.info('Removing folder "%s"...', dump_path)
            assert execute(["sudo", "rm", "-rf", dump_path]).returncode == 0


@pytest.fixture(name="bulk_setup", scope="session")
def _bulk_setup(test_site: Site, pytestconfig: pytest.Config) -> Iterator:
    """Setup multiple test hosts."""
    logger.info("Getting host names...")
    chunk_index = pytestconfig.getoption(name="--chunk-index")
    chunk_size = pytestconfig.getoption(name="--chunk-size")
    host_names = checks.get_host_names()[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
    checks.setup_hosts(test_site, host_names)
    yield
    checks.cleanup_hosts(test_site, host_names)
