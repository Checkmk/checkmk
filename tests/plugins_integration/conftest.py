# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator

import pytest

from tests.testlib.site import get_site_factory, Site, SiteFactory
from tests.testlib.utils import run
from tests.testlib.version import CMKVersion, edition_from_env

from tests.plugins_integration import checks

from cmk.utils.version import Edition

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
        "--enable-core-scheduling",
        action="store_true",
        default=False,
        help="Enable core scheduling (disabled by default)",
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
    for site in get_site_factory(prefix="plugins_").get_test_site(
        auto_cleanup=not checks.config.skip_cleanup
    ):
        dump_path = site.path("var/check_mk/dumps")
        checks.setup_site(site, dump_path)

        yield site

        if not request.config.getoption("--enable-core-scheduling"):
            site.stop_host_checks()
            site.stop_active_services()

        if not checks.config.skip_cleanup:
            # cleanup existing agent-output folder in the test site
            logger.info('Removing folder "%s"...', dump_path)
            assert run(["sudo", "rm", "-rf", dump_path]).returncode == 0


@pytest.fixture(name="site_factory_update", scope="session")
def _get_sf_update():
    base_version = CMKVersion("2.2.0p27", edition_from_env(fallback=Edition.CEE))
    return get_site_factory(prefix="update_", version=base_version)


@pytest.fixture(name="test_site_update", scope="session")
def _get_site_update(
    site_factory_update: SiteFactory, request: pytest.FixtureRequest
) -> Iterator[Site]:
    """Setup test-site and perform cleanup after test execution."""
    for site in site_factory_update.get_test_site(auto_cleanup=not checks.config.skip_cleanup):
        dump_path = site.path("var/check_mk/dumps")
        checks.setup_site(site, dump_path)

        yield site

        if not checks.config.skip_cleanup:
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
    if os.getenv("CLEANUP", "1") == "1" and not checks.config.skip_cleanup:
        checks.cleanup_hosts(test_site, host_names)


@pytest.fixture(name="plugin_validation_site", scope="session")
def _get_site_validation() -> Iterator[Site]:
    yield from get_site_factory(prefix="val_").get_test_site()
