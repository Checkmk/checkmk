#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Creating and deleting hosts in bulk, and what a site restart costs with them."""

import logging

from tests.performance.perftest import PerformanceTest
from tests.performance.sysmon import track_resources

logger = logging.getLogger(__name__)


def scenario_create_and_delete_hosts(
    perftest: PerformanceTest,
    restart_iterations: int = 0,
) -> None:
    """Scenario: Bulk host creation

    Create 100 hosts on each site (central site+remote sites).
    Activate the changes.
    Delete all hosts.
    Activate the changes."""
    hosts = perftest.generate_hosts(perftest.object_count, perftest.central_site, perftest.sites)
    hostnames = perftest.create_hosts(perftest.central_site, hosts)
    assert hostnames
    try:
        if restart_iterations:
            with track_resources("restart_central_site_with_hosts"):
                for _ in range(restart_iterations):
                    perftest.central_site.stop()
                    perftest.central_site.start()
    finally:
        if not perftest.central_site.is_running():
            perftest.central_site.start()
        perftest.central_site.ensure_running()
        perftest.delete_hosts(perftest.central_site, hostnames)
