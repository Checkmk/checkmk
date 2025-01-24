#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import get_services_with_status

from tests.plugins_integration.checks import (  # pylint: disable=ungrouped-imports
    get_host_names,
    setup_host,
)

logger = logging.getLogger(__name__)

# * Arista dumps containing several checks that have been removed after 2.3.0.
# * BIG-IP cluster containing several checks remaining in PEND state, leading to assertion-error
#   after update. See CMK-19103.
# * Ceph dump containing "Systemd Service Summary" changing between 2.3.0 and 2.4.0. SUP-21093.
SKIPPED_DUMPS = [
    "snmp-sw-arista.demo.checkmk.com_2_2_p12",
    "snmp-f5-bigip-failover-cluster",
    "agent-2.2.0p8-ceph-17.2.6",
]

# * The 'Postfix status' service has been renamed into 'Postfix status default'.
#   Related: CMK-13774
# * The 'Postfix Queue' has been renamed into 'Postfix Queue default'
#   See Werk #16377 or commit daf9d3ab9a5e9d698733f0af345d88120de863f0
# * The 'Power x' (x=1,2,...) services have been renamed into 'Power supply'
#   See Werk 16905.
# * "MSSQL Job: syspolicy_purge_history" service renamed between 2.3.0 and 2.4.0. See SUP-21714.
SKIPPED_CHECKS = [
    "Postfix status",
    "Postfix Queue",
    "Power 1",
    "MSSQL Job: syspolicy_purge_history",
    "MSSQL job syspolicy_purge_history",
]


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
    for host_name in (_ for _ in get_host_names() if _ not in SKIPPED_DUMPS):
        with setup_host(test_site_update, host_name, skip_cleanup=True):
            base_data[host_name] = test_site_update.get_host_services(host_name)

            for skipped_check in SKIPPED_CHECKS:
                if skipped_check in base_data[host_name]:
                    base_data[host_name].pop(skipped_check)

            base_data_status_0[host_name] = get_services_with_status(base_data[host_name], 0)
    test_site_update = site_factory_update.update_as_site_user(test_site_update)

    target_data = {}
    target_data_status_0 = {}
    for host_name in get_host_names(test_site_update):
        target_data[host_name] = test_site_update.get_host_services(host_name)

        for skipped_check in SKIPPED_CHECKS:
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
        get_host_names(test_site_update)
    )

    target_data_sd = {}
    target_data_sd_status_0 = {}
    for host_name in get_host_names(test_site_update):
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
