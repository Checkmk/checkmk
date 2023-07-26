#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import random
from pathlib import Path

import pytest

from tests.testlib.agent import register_controller, wait_until_host_receives_data
from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.hostaddress import HostName
from cmk.utils.version import Edition

from .conftest import (
    get_host_data,
    get_services_with_status,
    get_site_status,
    logger_services_crit,
    logger_services_ok,
    logger_services_warn,
    reschedule_services,
    update_config,
    update_site,
)

logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    os.environ.get("DISTRO") == "sles-15sp4",
    reason="Test currently failing for missing `php7`. "
    "This will be fixed  starting from  base-version 2.2.0p8",
)
def test_update(test_site: Site, agent_ctl: Path) -> None:  # pylint: disable=too-many-branches
    # get version data
    base_version = test_site.version

    hostnames = [HostName(f"test-host-{i}") for i in range(5)]
    hosts_folders = [f"/test-folder-{i}" for i in range(2)]

    logger.info("Creating new folders: %s", hosts_folders)
    for folder in hosts_folders:
        test_site.openapi.create_folder(folder)

    logger.info("Creating new hosts: %s", hostnames)
    test_site.openapi.bulk_create_hosts(
        [
            {
                "host_name": hostname,
                "folder": random.choice(hosts_folders),
                "attributes": {"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"},
            }
            for hostname in hostnames
        ],
        bake_agent=True,
        ignore_existing=True,
    )

    test_site.activate_changes_and_wait_for_core_reload()

    # perform hosts registration via the agent-ctl
    assert (
        len(hostnames) < 256
    ), "The current hosts-registration logic does not allow more than 255 hosts"

    for hostname in hostnames:
        address = f"127.0.0.{hostnames.index(hostname) + 1}"
        register_controller(agent_ctl, test_site, hostname, site_address=address)
        wait_until_host_receives_data(test_site, hostname)

    logger.info("Discovering services and waiting for completion...")
    test_site.openapi.bulk_discover_services(
        [str(hostname) for hostname in hostnames], wait_for_completion=True
    )
    test_site.openapi.activate_changes_and_wait_for_completion()

    base_data = {}
    base_ok_services = {}
    base_pend_services = {}
    base_warn_services = {}
    base_crit_services = {}

    for hostname in hostnames:
        reschedule_services(test_site, hostname)

        # get baseline monitoring data for each host
        base_data[hostname] = get_host_data(test_site, hostname)

        # TODO: 'Postfix Queue' and 'Postfix status' not found on Centos-8 and Almalinux-9 distros
        #  after the update. See CMK-13774.
        if os.environ.get("DISTRO") in ["centos-8", "almalinux-9"]:
            postfix_services = ["Postfix Queue", "Postfix status"]
            for postfix_service in postfix_services:
                if postfix_service in base_data[hostname]:
                    base_data[hostname].pop(postfix_service)

        base_ok_services[hostname] = get_services_with_status(base_data[hostname], "OK")
        base_pend_services[hostname] = get_services_with_status(base_data[hostname], "PEND")
        base_warn_services[hostname] = get_services_with_status(base_data[hostname], "WARN")
        base_crit_services[hostname] = get_services_with_status(base_data[hostname], "CRIT")

        assert len(base_ok_services[hostname]) > 0
        assert len(base_pend_services[hostname]) == 0

        logger_services_ok("base", base_ok_services[hostname], hostname)
        if len(base_warn_services[hostname]) > 0:
            logger_services_warn("base", base_warn_services[hostname], hostname)
        if len(base_crit_services[hostname]) > 0:
            logger_services_crit("base", base_crit_services[hostname], hostname)

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    target_site = update_site(test_site, target_version, interactive=True)

    # Triggering cmk config update
    update_config_result = update_config(target_site)

    assert update_config_result == 0, "Updating the configuration failed unexpectedly!"

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    logger.info("Discovering services and waiting for completion...")
    target_site.openapi.bulk_discover_services(
        [str(hostname) for hostname in hostnames], wait_for_completion=True
    )
    target_site.openapi.activate_changes_and_wait_for_completion()

    target_data = {}
    target_ok_services = {}
    target_pend_services = {}
    target_warn_services = {}
    target_crit_services = {}

    for hostname in hostnames:
        reschedule_services(target_site, hostname)

        # get update monitoring data
        target_data[hostname] = get_host_data(target_site, hostname)

        target_ok_services[hostname] = get_services_with_status(target_data[hostname], "OK")
        target_pend_services[hostname] = get_services_with_status(target_data[hostname], "PEND")
        target_warn_services[hostname] = get_services_with_status(target_data[hostname], "WARN")
        target_crit_services[hostname] = get_services_with_status(target_data[hostname], "CRIT")

        assert len(target_pend_services[hostname]) == 0

        logger_services_ok("target", target_ok_services[hostname], hostname)
        if len(target_warn_services[hostname]) > 0:
            logger_services_warn("target", target_warn_services[hostname], hostname)
        if len(target_crit_services[hostname]) > 0:
            logger_services_crit("target", target_crit_services[hostname], hostname)

        # TODO: 'Nullmailer Queue' service is not found after the update. Investigate.
        nullmailer_service = "Nullmailer Queue"
        if nullmailer_service in base_data[hostname]:
            base_data[hostname].pop(nullmailer_service)
            base_ok_services[hostname].remove(nullmailer_service)

        # TODO: 'OMD <sitename> apache' service is not found after the update. See CMK-14120.
        apache_service = f"OMD {test_site.id} apache"
        if apache_service in base_data[hostname]:
            base_data[hostname].pop(apache_service)
            base_ok_services[hostname].remove(apache_service)

        not_found_services = [
            service for service in base_data[hostname] if service not in target_data[hostname]
        ]
        err_msg = (
            f"In the {hostname} host the following services were found in base-version but not in "
            f"target-version: "
            f"{not_found_services}"
        )
        assert len(target_data[hostname]) >= len(base_data[hostname]), err_msg

        not_ok_services = [
            service
            for service in base_ok_services[hostname]
            if service not in target_ok_services[hostname]
        ]
        err_msg = (
            f"In the {hostname} host the following services were `OK` in base-version but not in "
            f"target-version: "
            f"{not_ok_services}"
        )
        assert set(base_ok_services[hostname]).issubset(set(target_ok_services[hostname])), err_msg
