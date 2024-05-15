#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os

import pytest

from tests.testlib.agent import wait_until_host_receives_data
from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name, get_services_with_status, repo_path
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.hostaddress import HostName
from cmk.utils.version import Edition

from .conftest import get_site_status, update_site

logger = logging.getLogger(__name__)


@pytest.mark.cee
def test_update_rules(
    test_setup: tuple[Site, bool],
) -> None:
    test_site, disable_interactive_mode = test_setup
    base_version = test_site.version

    host_name = HostName("test-rules")
    host_group_name = "test-rules"

    logger.info("Creating new host: %s", host_name)
    test_site.openapi.create_host(
        hostname=host_name,
        folder="/",
        attributes={"ipaddress": "127.0.0.1", "tag_agent": "no-agent"},
        bake_agent=False,
    )
    logger.info("Creating new host group: %s", host_group_name)
    test_site.openapi.create_host_group(host_group_name, host_group_name)

    test_site.activate_changes_and_wait_for_core_reload()
    wait_until_host_receives_data(test_site, host_name)

    logger.info("Discovering services and waiting for completion...")
    test_site.openapi.bulk_discover_services_and_wait_for_completion([host_name])
    test_site.openapi.activate_changes_and_wait_for_completion()

    base_data = {}
    base_ok_services = {}

    test_site.reschedule_services(host_name)

    # get baseline monitoring data for each host(s)
    base_data[host_name] = test_site.get_host_services(host_name)
    ignore_data = [
        # OMD status service turning into CRIT after the update (looks like for performance reasons)
        # See CMK-16608. TODO: restore service after ticket is done.
        f"OMD {test_site.id} status",
        # "Notification Spooler" results in "No status information, Spooler not running"
        # See CMK-16760. TODO: restore service after ticket is done.
        f"OMD {test_site.id} Notification Spooler",
    ]

    for data in ignore_data:
        if data in base_data[host_name]:
            base_data[host_name].pop(data)

    base_ok_services[host_name] = get_services_with_status(base_data[host_name], 0)

    assert len(base_ok_services[host_name]) > 0

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    test_site.activate_changes_and_wait_for_core_reload()

    rules_folder = repo_path() / "tests" / "update" / "rules"
    try:
        with open(rules_folder / "ignore.txt", "r", encoding="UTF-8") as ignore_list_file:
            ignore_list = [_ for _ in ignore_list_file.read().splitlines() if _]
    except FileNotFoundError:
        ignore_list = []
    rules_file_names = [
        _ for _ in os.listdir(rules_folder) if _.endswith(".json") and _ not in ignore_list
    ]
    for rules_file_name in rules_file_names:
        rules_file_path = rules_folder / rules_file_name
        with open(rules_file_path, "r", encoding="UTF-8") as ruleset_file:
            logger.info('Importing rules file "%s"...', rules_file_path)
            rules = json.load(ruleset_file)
            for rule in rules:
                test_site.openapi.create_rule(value=rule)
    test_site.activate_changes_and_wait_for_core_reload()

    target_site = update_site(test_site, target_version, not disable_interactive_mode)

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    logger.info("Discovering services and waiting for completion...")
    target_site.openapi.bulk_discover_services_and_wait_for_completion([str(host_name)])
    target_site.openapi.activate_changes_and_wait_for_completion()

    target_data = {}
    target_ok_services = {}

    target_site.reschedule_services(host_name)

    # get update monitoring data
    target_data[host_name] = target_site.get_host_services(host_name)

    target_ok_services[host_name] = get_services_with_status(target_data[host_name], 0)

    not_found_services = [
        service for service in base_data[host_name] if service not in target_data[host_name]
    ]
    err_msg = (
        f"In the {host_name} host the following services were found in base-version but not in "
        f"target-version: "
        f"{not_found_services}"
    )
    assert len(target_data[host_name]) >= len(base_data[host_name]), err_msg

    not_ok_services = [
        service
        for service in base_ok_services[host_name]
        if service not in target_ok_services[host_name]
    ]
    err_msg = (
        f"In the {host_name} host the following services were `OK` in base-version but not in "
        f"target-version: "
        f"{not_ok_services}"
        f"\nDetails: {[(s, target_data[host_name][s].summary) for s in not_ok_services]})"
    )
    assert base_ok_services[host_name].issubset(target_ok_services[host_name]), err_msg
