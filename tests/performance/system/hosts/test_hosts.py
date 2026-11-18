#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: creating and deleting hosts in bulk."""

from collections.abc import Iterator
from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.system.hosts import scenario
from tests.performance.system.perftest import PerformanceTest


@pytest.fixture(name="bulk_created_hosts")
def _bulk_created_hosts(perftest: PerformanceTest) -> Iterator[None]:
    """Create 100 hosts on each site once, for all rounds of a restart."""
    hosts = perftest.generate_hosts(perftest.object_count, perftest.central_site, perftest.sites)
    hostnames = perftest.create_hosts(perftest.central_site, hosts)
    assert hostnames
    try:
        # A warmup restart: the first one right after activating the hosts is not measured. A
        # warmup round would be, as the scenario tracks its resources itself.
        perftest.central_site.stop()
        perftest.central_site.start()
        yield
    finally:
        if not perftest.central_site.is_running():
            perftest.central_site.start()
        perftest.central_site.ensure_running()
        perftest.delete_hosts(perftest.central_site, hostnames)


@pytest.mark.usefixtures("bulk_created_hosts")
def test_performance_hosts_restart(
    request: pytest.FixtureRequest, perftest: PerformanceTest, benchmark: BenchmarkFixture
) -> None:
    """Site restart with bulk-created hosts"""
    benchmark.pedantic(
        partial(scenario.scenario_restart_site, perftest, request.node.name),
        rounds=perftest.rounds,
    )


@pytest.mark.usefixtures("track_system_resources")
def test_performance_hosts(perftest_dist: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk host creation across a distributed setup"""
    benchmark.pedantic(
        partial(scenario.scenario_create_and_delete_hosts, perftest_dist),
        args=[],
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )
