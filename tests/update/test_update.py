#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_services_with_status, version_spec_from_env
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.hostaddress import HostName
from cmk.utils.version import Edition

from .conftest import get_site_status, update_site

logger = logging.getLogger(__name__)


@pytest.mark.cse
@pytest.mark.cee
def test_update(test_setup: tuple[Site, Edition, bool]) -> None:
    test_site, target_edition, interactive_mode = test_setup
    base_version = test_site.version
    hostname = HostName("test-host")
    ip_address = "127.0.0.1"

    logger.info("Creating new host: %s", hostname)
    test_site.openapi.create_host(
        hostname=hostname, attributes={"ipaddress": ip_address, "tag_agent": "cmk-agent"}
    )
    test_site.activate_changes_and_wait_for_core_reload()

    base_data: dict = {}
    base_ok_services: set[str] = set()
    if not version_from_env().is_saas_edition():
        logger.info("Discovering services and waiting for completion...")
        test_site.openapi.bulk_discover_services_and_wait_for_completion([str(hostname)])
        test_site.openapi.activate_changes_and_wait_for_completion()
        test_site.schedule_check(hostname, "Check_MK", 0)

        # get baseline monitoring data for each host
        base_data = test_site.get_host_services(hostname)

        base_ok_services = get_services_with_status(base_data, 0)
        assert len(base_ok_services) > 0

    target_version = CMKVersion(version_spec_from_env(CMKVersion.DAILY), target_edition)
    target_site = update_site(test_site, target_version, interactive_mode)

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    if not version_from_env().is_saas_edition():
        logger.info("Discovering services and waiting for completion...")
        target_site.openapi.bulk_discover_services_and_wait_for_completion([str(hostname)])
        target_site.openapi.activate_changes_and_wait_for_completion()
        target_site.schedule_check(hostname, "Check_MK", 0)

        # get update monitoring data
        target_data = target_site.get_host_services(hostname)
        target_ok_services = get_services_with_status(target_data, 0)

        not_found_services = [service for service in base_data if service not in target_data]
        err_msg = (
            f"The following services were found in base-version but not in target-version: "
            f"{not_found_services}"
        )
        assert len(target_data) >= len(base_data), err_msg

        not_ok_services = [
            service for service in base_ok_services if service not in target_ok_services
        ]
        err_details = [
            (s, "state: " + str(target_data[s].state), target_data[s].summary)
            for s in not_ok_services
        ]
        err_msg = (
            f"The following services were `OK` in base-version but not in target-version: "
            f"{not_ok_services}"
            f"\nDetails: {err_details})"
        )
        assert base_ok_services.issubset(target_ok_services), err_msg
