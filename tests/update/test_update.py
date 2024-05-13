#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import random
from pathlib import Path

import pytest

from tests.testlib.agent import (
    register_controller,
    wait_for_agent_cache_omd_status,
    wait_until_host_receives_data,
)
from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name, get_services_with_status
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.hostaddress import HostName
from cmk.utils.version import Edition

from .conftest import get_site_status, update_site

logger = logging.getLogger(__name__)


@pytest.mark.cee
def test_update(  # pylint: disable=too-many-branches
    test_setup: tuple[Site, bool],
    agent_ctl: Path,
) -> None:
    test_site, disable_interactive_mode = test_setup
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
    test_site.openapi.bulk_discover_services_and_wait_for_completion(
        [str(hostname) for hostname in hostnames]
    )
    test_site.openapi.activate_changes_and_wait_for_completion()

    base_data = {}
    base_ok_services = {}

    for hostname in hostnames:
        test_site.reschedule_services(hostname)

        # get baseline monitoring data for each host
        base_data[hostname] = test_site.get_host_services(hostname)

        # * The 'Postfix status' service has been renamed into 'Postfix status default'.
        #   Related: CMK-13774
        # * The 'Postfix Queue' has been renamed into 'Postfix Queue default'
        #   See Werk #16377 or commit daf9d3ab9a5e9d698733f0af345d88120de863f0
        for changed_service in ["Postfix status", "Postfix Queue"]:
            if changed_service in base_data[hostname]:
                base_data[hostname].pop(changed_service)

        base_ok_services[hostname] = get_services_with_status(base_data[hostname], 0)
        # used in debugging mode
        _ = get_services_with_status(base_data[hostname], 1)  # Warn
        _ = get_services_with_status(base_data[hostname], 2)  # Crit
        _ = get_services_with_status(base_data[hostname], 3)  # Unknown

        assert len(base_ok_services[hostname]) > 0

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    target_site = update_site(test_site, target_version, not disable_interactive_mode)

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    logger.info("Discovering services and waiting for completion...")
    target_site.openapi.bulk_discover_services_and_wait_for_completion(
        [str(hostname) for hostname in hostnames]
    )
    target_site.openapi.activate_changes_and_wait_for_completion()

    target_data = {}
    target_ok_services = {}

    # services such as 'omd status' rely on cache data:
    # wait for the cache to be up-to-date and reschedule services
    wait_for_agent_cache_omd_status(target_site)
    for hostname in hostnames:
        target_site.schedule_check(hostname, "Check_MK", 0)

    for hostname in hostnames:
        target_site.reschedule_services(hostname)

        # get update monitoring data
        target_data[hostname] = target_site.get_host_services(hostname)

        target_ok_services[hostname] = get_services_with_status(target_data[hostname], 0)
        # used in debugging mode
        _ = get_services_with_status(target_data[hostname], 1)  # Warn
        _ = get_services_with_status(target_data[hostname], 2)  # Crit
        _ = get_services_with_status(target_data[hostname], 3)  # Unknown

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
        err_details = [
            (s, "state: " + str(target_data[hostname][s].state), target_data[hostname][s].summary)
            for s in not_ok_services
        ]
        err_msg = (
            f"In the {hostname} host the following services were `OK` in base-version but not in "
            f"target-version: "
            f"{not_ok_services}"
            f"\nDetails: {err_details})"
        )
        assert base_ok_services[hostname].issubset(target_ok_services[hostname]), err_msg
