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


def test_plugin_update(test_site_update: Site, site_factory_update: SiteFactory) -> None:
    """Test performing the following steps:

    * Initialize test-site with min-version and discover services from injected agent-dumps and
        SNMP walks;
    * Update test-site to daily CEE version of the current branch;
    * Compare services found before and after the update;
    * Re-discover services and compare services found before and after such discovery.
    """
    base_data = {}
    base_data_status_0 = {}
    for host_name in get_host_names():
        with setup_host(test_site_update, host_name, skip_cleanup=True):
            base_data[host_name] = test_site_update.get_host_services(host_name)

            # The 'Postfix status' service has been renamed into 'Postfix status default'.
            # Related: CMK-13774
            if "Postfix status" in base_data[host_name]:
                base_data[host_name].pop("Postfix status")

            base_data_status_0[host_name] = get_services_with_status(base_data[host_name], 0)

    test_site_update = site_factory_update.update_as_site_user(test_site_update)

    target_data = {}
    target_data_status_0 = {}
    for host_name in get_host_names(test_site_update):
        target_data[host_name] = test_site_update.get_host_services(host_name)

        # The 'Postfix status' service has been renamed into 'Postfix status default'.
        # Related: CMK-13774
        if "Postfix status" in target_data[host_name]:
            target_data[host_name].pop("Postfix status")

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

    test_site_update.openapi.bulk_discover_services(get_host_names(test_site_update))

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
