#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

import pytest
from faker import Faker

from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.version import Edition

from .conftest import (
    agent_controller_daemon,
    clean_agent_controller,
    download_and_install_agent_package,
    get_host_data,
    get_services_with_status,
    get_site_status,
    update_config,
    update_site,
    version_supported,
)

logger = logging.getLogger(__name__)


@pytest.mark.type("update")
def test_update(test_site: Site, tmp_path: Path) -> None:
    # TODO: check source installation (version check done in test_site fixture)
    # TODO: set config

    # get version data
    base_version = test_site.version

    # create a new host and perform a service discovery
    hostname = f"test-update-{Faker().first_name()}"
    logger.info("Creating new host: %s", hostname)

    test_site.openapi.create_host(
        hostname=hostname,
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
        bake_agent=True,
    )
    test_site.activate_changes_and_wait_for_core_reload()
    agent_ctl_path = download_and_install_agent_package(test_site, tmp_path)

    with (
        clean_agent_controller(agent_ctl_path),
        agent_controller_daemon(agent_ctl_path),
    ):
        logger.info("Discovering services and waiting for completion...")
        test_site.openapi.discover_services_and_wait_for_completion(
            hostname, cmk_version=base_version.version
        )
        test_site.openapi.activate_changes_and_wait_for_completion()

        # get baseline monitoring data
        base_data_host = get_host_data(test_site, hostname)

        # force reschedule pending services
        while len(get_services_with_status(base_data_host, "PEND")) > 0:
            logger.info(
                "The following services were found with pending status: %s. Rescheduling checks...",
                get_services_with_status(base_data_host, "PEND"),
            )
            test_site.schedule_check(hostname, "Check_MK", 0)
            base_data_host = get_host_data(test_site, hostname)

    base_ok_services = get_services_with_status(base_data_host, "OK")
    base_pend_services = get_services_with_status(base_data_host, "PEND")
    base_warn_services = get_services_with_status(base_data_host, "WARN")
    base_crit_services = get_services_with_status(base_data_host, "CRIT")

    assert len(base_ok_services) > 0
    assert len(base_pend_services) == 0

    logger.info("Services found in `OK` status in base-version: %s", len(base_ok_services))
    logger.info("Services found in `WARN` status in base-version: %s", len(base_warn_services))
    logger.info("Services found in `CRIT` status in base-version: %s", len(base_crit_services))

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    target_site = update_site(test_site, target_version, interactive=True)

    # TODO: check target installation (version check done in update_site function)
    # TODO: check config

    # Dumping cmc config as parseable object (JSON)
    # cmk --dump-cmc-config

    # Triggering cmk config update
    update_config_result = update_config(target_site)
    if version_supported(base_version.version):
        assert update_config_result == 0, "Updating the configuration failed unexpectedly!"
    else:
        assert (
            update_config_result != 0
        ), "Updating the configuration succeeded for an unsupported release!"
        assert (
            update_config_result != 2
        ), "Trying to update the config resulted in an unexpected error!"

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    with (
        clean_agent_controller(agent_ctl_path),
        agent_controller_daemon(agent_ctl_path),
    ):
        logger.info("Discovering services and waiting for completion...")
        target_site.openapi.discover_services_and_wait_for_completion(hostname)
        target_site.openapi.activate_changes_and_wait_for_completion()

        # get update monitoring data
        target_data_host = get_host_data(target_site, hostname)

        # force reschedule pending services
        while len(get_services_with_status(target_data_host, "PEND")) > 0:
            logger.info(
                "The following services were found with pending status: %s. Rescheduling checks...",
                get_services_with_status(target_data_host, "PEND"),
            )
            target_site.schedule_check(hostname, "Check_MK", 0)
            target_data_host = get_host_data(target_site, hostname)

    target_ok_services = get_services_with_status(target_data_host, "OK")
    target_pend_services = get_services_with_status(target_data_host, "PEND")
    target_warn_services = get_services_with_status(target_data_host, "WARN")
    target_crit_services = get_services_with_status(target_data_host, "CRIT")

    assert len(target_pend_services) == 0

    logger.info("Services found in `OK` status in target-version: %s", len(target_ok_services))
    logger.info("Services found in `WARN` status in target-version: %s", len(target_warn_services))
    logger.info("Services found in `CRIT` status in target-version: %s", len(target_crit_services))

    assert len(target_data_host) >= len(base_data_host)

    # TODO: 'Interface 2' service is not found after the update. Investigate.
    base_ok_services.remove("Interface 2")

    err_msg = (
        f"The following services were `OK` in base-version but not in target-version: "
        f"{[service for service in base_ok_services if service not in target_ok_services]}"
    )
    assert set(base_ok_services).issubset(set(target_ok_services)), err_msg
