#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os
from collections.abc import Iterator
from datetime import datetime as dt
from datetime import timezone as tz
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.testlib.agent_dumps import inject_dumps
from tests.testlib.licensing import license_site, site_license_response
from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.setup.licensing import Licensing
from tests.testlib.pytest_helpers.marks import (
    skip_if_enterprise_edition,
    skip_if_not_saas_edition,
    skip_if_raw_edition,
    skip_if_saas_edition,
)
from tests.testlib.site import Site
from tests.testlib.utils import ServiceInfo

from cmk.ccc.version import Edition

logger = logging.getLogger(__name__)

MODULE_PATH = Path(__file__).parent.resolve()
DUMPS_DIR = MODULE_PATH / "dumps"


def _update_license_usage(site: Site) -> None:
    site.delete_file("var/check_mk/licensing/next_run")
    site.run(["cmk-update-license-usage"])


@pytest.fixture(name="licensing_page", scope="function")
def _licensing_page(dashboard_page: Dashboard) -> Iterator[Licensing]:
    yield Licensing(dashboard_page.page)


@pytest.fixture(name="licensing_hosts", scope="session")
def _licensing_hosts(test_site: Site) -> Iterator[dict[str, dict[str, ServiceInfo]]]:
    """Create some hosts to have services in the site"""
    inject_dumps(test_site, dumps_dir=DUMPS_DIR)
    host_count = 3
    host_names = ["licensing_host%s" % id for id in range(1, host_count + 1)]
    hosts = [
        {
            "host_name": host_name,
            "folder": "/",
            "attributes": {
                "ipaddress": "127.0.0.%03d" % id,
                "tag_agent": "cmk-agent",
            },
        }
        for id, host_name in enumerate(host_names)
    ]
    try:
        test_site.openapi.bulk_create_hosts(hosts)
        test_site.openapi.activate_changes_and_wait_for_completion()

        logger.info("Discovering services and waiting for completion...")
        test_site.openapi.bulk_discover_services_and_wait_for_completion(host_names)
        test_site.openapi.activate_changes_and_wait_for_completion()
        host_services = {}
        for host_name in host_names:
            test_site.schedule_check(host_name, "Check_MK")
            host_services[host_name] = test_site.get_host_services(host_name)
        _update_license_usage(test_site)
        yield host_services
    finally:
        if os.getenv("CLEANUP", "1") == "1":
            test_site.openapi.bulk_delete_hosts(host_names)
            test_site.openapi.activate_changes_and_wait_for_completion()


@skip_if_raw_edition
@skip_if_saas_edition
@pytest.mark.parametrize(
    "service_limit", [-1, 3, 100000], ids=["unlimited_services", "3_services", "100k_services"]
)
def test_license_valid(
    test_site: Site,
    licensing_page: Licensing,
    service_limit: int,
) -> None:
    """Test a valid license (CEE+CCE+CME)"""
    with license_site(test_site, license_validity_days=90, service_limit=service_limit) as (
        verification_request,
        verification_response,
    ):
        # Reload to update license information
        licensing_page.page.reload()

        logger.info(
            "VerificationRequest: %s", json.dumps(verification_request.for_report(), indent=4)
        )

        logger.info(
            "VerificationResponse: %s", json.dumps(verification_response.for_report(), indent=4)
        )

        if test_site.version.edition != Edition.CEE:
            # Current license state
            assert licensing_page.get_named_value("License state") == "Licensed"
            assert licensing_page.get_named_value("Instance ID") != ""

            # Last successful verification
            assert licensing_page.get_named_value("Time")
            assert not licensing_page.get_named_value("Result")

        # License details
        assert licensing_page.get_named_value("License start") == dt.fromtimestamp(
            verification_response.subscription_start_ts, tz.utc
        ).strftime("%Y-%m-%d")
        assert licensing_page.get_named_value("License end") == dt.fromtimestamp(
            verification_response.subscription_start_ts + 86400 * 90, tz.utc
        ).strftime("%Y-%m-%d")
        assert (
            licensing_page.get_named_value("Licensed services").lower() == "unlimited"
            if service_limit == -1
            else str(service_limit)
        )
        assert licensing_page.get_named_value("Checkmk edition") == test_site.version.edition.title
        assert licensing_page.get_named_value("Options") == "Ntopng integration"
        assert licensing_page.get_named_value("Reseller") == "-"
        assert licensing_page.get_named_value("Operational state") == "Active"
        assert licensing_page.get_named_value("Automatic renewal") == "No"

        # No warning displayed
        expect(licensing_page.main_area.locator("div.warning")).to_have_count(0)


@skip_if_raw_edition
@skip_if_saas_edition
@skip_if_enterprise_edition
def test_license_invalid_edition(
    test_site: Site,
    licensing_page: Licensing,
) -> None:
    """Test an invalid license for the current edition (CCE+CME)"""
    with license_site(test_site, edition=Edition.CEE, license_validity_days=90):
        # Reload to update license information
        licensing_page.page.reload()

        # Assert for banner: license violation due to invalid edition
        assert (warning := (licensing_page.main_area.locator("div.warning").text_content()))
        assert "Unlicensed Checkmk edition" in warning
        assert f"using {test_site.version.edition.title}" in warning
        assert "not included in the applied license" in warning
        assert f"licensed edition: {Edition.CEE.title}" in warning

        # Current license state - we actually expect the license to be valid (just not "suitable")
        assert licensing_page.get_named_value("License state") == "Licensed"

        # License details
        assert licensing_page.get_named_value("Checkmk edition") == Edition.CEE.title


@skip_if_raw_edition
@skip_if_saas_edition
@skip_if_enterprise_edition
def test_license_trial(
    test_site: Site,
    licensing_page: Licensing,
) -> None:
    """Test a trial license (CEE+CCE+CME)"""
    with site_license_response(test_site):
        # do not write an actual license response but use an empty file
        # restart the core to make sure the empty license is picked up
        test_site.restart_core()

        # Reload to update license information
        licensing_page.page.reload()

        assert licensing_page.get_named_value("License state") == "30 days left in your free trial"


@skip_if_not_saas_edition
@pytest.mark.parametrize("service_limit", [5000], ids=["5k_services"])
def test_license_valid_saas(
    test_site: Site,
    dashboard_page: Dashboard,
    service_limit: int,
    licensing_hosts: dict[str, dict[str, ServiceInfo]],
) -> None:
    """Test a valid license (CSE)"""
    with license_site(
        test_site,
        edition=Edition.CSE,
        license_validity_days=90,
        service_limit=service_limit,
    ):
        # Reload to update license information
        dashboard_page.page.reload()

        # Check if service limit warning is detected
        assert (warning := (dashboard_page.main_area.locator("div.warning").text_content()))
        assert f"limited to {service_limit} services" in warning
        assert "beta phase" in warning
