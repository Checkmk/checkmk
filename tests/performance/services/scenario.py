#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Discovering the services of freshly created hosts, in bulk."""

import logging

from tests.performance.perftest import PerformanceTest

logger = logging.getLogger(__name__)


def scenario_performance_services(
    perftest: PerformanceTest,
) -> None:
    """Scenario: Bulk service discovery

    Create 100 hosts on the central site.
    Activate changes.
    Discover services.
    Drop the hosts.
    Activate changes.
    """
    hosts = perftest.generate_hosts(perftest.object_count, perftest.central_site)
    hostnames = perftest.create_hosts(perftest.central_site, hosts)
    assert hostnames
    try:
        perftest.discover_services(perftest.central_site, hostnames)
    finally:
        existing_host_names = perftest.central_site.openapi.hosts.get_all_names()
        missing_host_names = [_ for _ in hostnames if _ not in existing_host_names]
        logger.info(
            "The following %s hosts have been created: %s",
            len(existing_host_names),
            existing_host_names,
        )
        if len(missing_host_names) > 0:
            logger.warning(
                "The following %s hosts are missing: %s",
                len(missing_host_names),
                missing_host_names,
            )
        if len(hostnames) > 0:
            perftest.delete_hosts(perftest.central_site, hostnames)
