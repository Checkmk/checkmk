#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

import pytest

from tests.testlib.agent_dumps import inject_dumps
from tests.testlib.site import Site
from tests.testlib.utils import edition_from_env, parse_raw_edition
from tests.testlib.version import version_from_env

from tests.update.helpers import (
    BaseVersions,
    bulk_discover_and_schedule,
    create_password,
    create_site,
    DUMPS_DIR,
    inject_rules,
    TestParams,
)

from cmk.ccc.version import Edition

logger = logging.getLogger(__name__)


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
    config.addinivalue_line("markers", "cre: marks tests using a raw-edition site")
    config.addinivalue_line("markers", "cee: marks tests using an enterprise-edition site")
    config.addinivalue_line("markers", "cce: marks tests using a cloud-edition site")
    config.addinivalue_line("markers", "cse: marks tests using a saas-edition site")
    config.addinivalue_line("markers", "cme: marks tests using a managed-edition site")


@contextmanager
def _setup_host(site: Site, hostname: str, ip_address: str) -> Generator[None]:
    try:
        logger.info("Creating new host: %s", hostname)
        site.openapi.hosts.create(
            hostname=hostname, attributes={"ipaddress": ip_address, "tag_agent": "cmk-agent"}
        )
        site.activate_changes_and_wait_for_core_reload()

        bulk_discover_and_schedule(site, hostname)
        yield
    finally:
        site.openapi.hosts.delete(hostname=hostname)
        site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(name="test_setup", params=TestParams.TEST_PARAMS, scope="module")
def _setup(
    request: pytest.FixtureRequest,
) -> Generator[tuple[Site, Edition, bool, str]]:
    """Install the test site with the base version."""
    base_package, interactive_mode = request.param
    target_edition_raw = request.config.getoption(name="--target-edition")
    target_edition = (
        parse_raw_edition(target_edition_raw)
        if target_edition_raw
        else edition_from_env(Edition.CEE)
    )
    logger.info("Base edition: %s", base_package.edition.short)
    logger.info("Target edition: %s", target_edition.short)

    if (
        request.config.getoption(name="--latest-base-version")
        and base_package.version != BaseVersions.BASE_VERSIONS[-1]
    ):
        pytest.skip("Only latest base-version selected")

    interactive_mode = interactive_mode and not request.config.getoption(
        name="--disable-interactive-mode"
    )
    logger.info("Setting up test-site ...")
    test_site = create_site(base_package)
    try:
        inject_dumps(test_site, DUMPS_DIR)
        create_password(test_site)
        disable_rules_injection = request.config.getoption(name="--disable-rules-injection")
        if not version_from_env().is_saas_edition():
            if not disable_rules_injection:
                inject_rules(test_site)

        hostname = "test-host"
        with _setup_host(test_site, hostname=hostname, ip_address="127.0.0.1"):
            yield test_site, target_edition, interactive_mode, hostname
    finally:
        cleanup = os.getenv("CLEANUP", "1") == "1"
        test_site.save_results()
        if cleanup:
            test_site.rm()
