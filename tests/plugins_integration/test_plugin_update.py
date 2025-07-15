#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from tests.testlib.agent_dumps import get_dump_and_walk_names
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import get_services_with_status

from tests.plugins_integration.checks import (
    config,
    setup_host,
)

logger = logging.getLogger(__name__)


@pytest.fixture(name="skip_dumps", scope="module")
def _skip_dumps():
    # * Arista dumps containing several checks that have been removed after 2.3.0.
    # * BIG-IP cluster containing several checks remaining in PEND state, leading to assertion-error
    #   after update. See CMK-19103.
    # * Ceph dump containing "Systemd Service Summary" changing between 2.3.0 and 2.4.0. SUP-21093.
    # * Proxmox dump containing "Systemd Service Summary" changing between versions. SUP-22010.
    config.skipped_dumps = [
        "snmp-sw-arista.demo.checkmk.com_2_2_p12",
        "snmp-f5-bigip-failover-cluster",
        "agent-2.2.0p8-ceph-17.2.6",
        "agent-2.2.0p14-proxmox",
    ]
    try:
        yield
    finally:
        config.skipped_dumps = []


@pytest.fixture(name="skip_checks", scope="module")
def _skip_checks():
    # * The 'Postfix status' service has been renamed into 'Postfix status default'.
    #   Related: CMK-13774
    # * The 'Postfix Queue' has been renamed into 'Postfix Queue default'
    #   See Werk #16377 or commit daf9d3ab9a5e9d698733f0af345d88120de863f0
    # * The 'Power x' (x=1,2,...) services have been renamed into 'Power supply'
    #   See Werk 16905.
    # * The 'Proxmox VE Node Info' service shows a flaky behavior after update.
    #   Related: CMK-24198
    config.skipped_checks = ["Postfix status", "Postfix Queue", "Power 1", "Proxmox VE Node Info"]
    try:
        yield
    finally:
        config.skipped_checks = []


@pytest.mark.usefixtures("skip_checks", "skip_dumps")
def test_plugin_update(
    test_site_update: Site,
    site_factory_update: SiteFactory,
    create_periodic_service_discovery_rule: None,
) -> None:
    """Test performing the following steps:

    * Initialize test-site with min-version and discover services from injected agent-dumps and
        SNMP walks;
    * Update test-site to daily CEE version of the current branch;
    * Compare services found before and after the update;
    * Re-discover services and compare services found before and after such discovery;
    * Check the number of rules in the ruleset 'periodic_discovery' and compare with the expected.
    """
    psd_rules_base = test_site_update.openapi.rules.get_all("periodic_discovery")
    base_data = {}
    base_data_status_0 = {}
    hostnames = get_dump_and_walk_names(
        config.dump_dir_integration, config.skipped_dumps
    ) + get_dump_and_walk_names(config.dump_dir_siteless, config.skipped_dumps)
    for host_name in hostnames:
        with setup_host(test_site_update, host_name, skip_cleanup=True):
            base_data[host_name] = test_site_update.get_host_services(host_name)

            for skipped_check in config.skipped_checks:
                if skipped_check in base_data[host_name]:
                    base_data[host_name].pop(skipped_check)

            base_data_status_0[host_name] = get_services_with_status(base_data[host_name], 0)
    test_site_update = site_factory_update.update_as_site_user(test_site_update)
    test_site_update.openapi.changes.activate_and_wait_for_completion()

    target_data = {}
    target_data_status_0 = {}
    for host_name in test_site_update.openapi.hosts.get_all_names():
        target_data[host_name] = test_site_update.get_host_services(host_name)

        for skipped_check in config.skipped_checks:
            if skipped_check in target_data[host_name]:
                target_data[host_name].pop(skipped_check)

        target_data_status_0[host_name] = get_services_with_status(target_data[host_name], 0)

        not_found_services = [
            service for service in base_data[host_name] if service not in target_data[host_name]
        ]
        not_found_status_0_services = [
            service
            for service in base_data_status_0[host_name]
            if service not in target_data_status_0[host_name]
        ]
        assert len(base_data[host_name]) <= len(target_data[host_name]), (
            f"The following services are found in {host_name} in base-version but not in "
            f"target-version: {not_found_services}"
        )
        assert base_data_status_0[host_name].issubset(target_data_status_0[host_name]), (
            f"The following services are found in state=0 in {host_name} in base-version but not "
            f"in target-version: {not_found_status_0_services}"
        )

    test_site_update.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion(
        test_site_update.openapi.hosts.get_all_names()
    )
    test_site_update.openapi.changes.activate_and_wait_for_completion()

    target_data_sd = {}
    target_data_sd_status_0 = {}
    for host_name in test_site_update.openapi.hosts.get_all_names():
        target_data_sd[host_name] = test_site_update.get_host_services(host_name)
        target_data_sd_status_0[host_name] = get_services_with_status(target_data_sd[host_name], 0)

        not_found_services_sd = [
            service
            for service in target_data[host_name]
            if service not in target_data_sd[host_name]
        ]
        not_found_status_0_services_sd = [
            service
            for service in target_data_status_0[host_name]
            if service not in target_data_sd_status_0[host_name]
        ]

        assert len(target_data[host_name]) <= len(target_data_sd[host_name]), (
            f"The following services are found in {host_name} in target-version before "
            f"service-discovery but not after: {not_found_services_sd}"
        )
        assert target_data_status_0[host_name].issubset(target_data_sd_status_0[host_name]), (
            f"The following services are found in state=0 in {host_name} target-version before "
            f"service-discovery but not after: {not_found_status_0_services_sd}"
        )

    psd_rules_update = test_site_update.openapi.rules.get_all("periodic_discovery")
    err_msg = (
        "The number of rules in the ruleset 'periodic_discovery' differs between before and after "
        "the update."
        "Details:"
        f"\nPSD rules before the update: \n{psd_rules_base}"
        f"\nPSD rules after the update: \n{psd_rules_update}"
    )
    assert len(psd_rules_update) == len(psd_rules_base), err_msg
