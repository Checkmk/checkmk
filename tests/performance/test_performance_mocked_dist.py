#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Performance test: Distributed setup with mocked remote sites (CMK-35259)

Benchmarks the central site's bulk change activation against a scalable number
of mocked remote sites (default: 30, see --mocked-sites). The mock sites
implement the remote side of the activate changes protocol (config sync,
activation, broker certificates) and a minimal livestatus endpoint, so the
central site performs its full per-site activation work while the remote-side
activation cost is excluded by design. See mock_remote_sites.py for details.

The two tests measure the identical change set (host tag groups, folder
hierarchy and hosts spread over all mocked sites) with the distributed
piggyback feature disabled and enabled, to determine the activation overhead
of distributed piggyback at a realistic site count.
"""

import logging
from collections.abc import Iterator

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.perftest import PerformanceTest
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="perftest_mocked_dist", scope="module")
def _perftest_mocked_dist(
    central_site: Site, pytestconfig: pytest.Config
) -> Iterator[PerformanceTest]:
    """Performance test with a central site and mocked remote sites"""
    yield PerformanceTest(central_site, remote_sites=None, pytestconfig=pytestconfig)


@pytest.fixture(name="mocked_remote_site_ids", scope="module")
def _mocked_remote_site_ids(perftest_mocked_dist: PerformanceTest) -> Iterator[list[str]]:
    """Register the mocked remote sites and spread the bulk changes over them."""
    with perftest_mocked_dist.mocked_remote_sites_environment() as site_ids:
        perftest_mocked_dist.bulk_change_target_site_ids = site_ids
        try:
            yield site_ids
        finally:
            perftest_mocked_dist.bulk_change_target_site_ids = None


@pytest.fixture(name="mocked_distributed_piggyback")
def _mocked_distributed_piggyback(
    perftest_mocked_dist: PerformanceTest, mocked_remote_site_ids: list[str]
) -> Iterator[None]:
    """Enable the piggyback hub and create piggybacked hosts on the mocked sites.

    The total piggybacked host count (see --pb-hosts; default 2 * object_count,
    matching the real-remote-site variant of this scenario) is spread evenly
    over the mocked sites. With fewer piggybacked hosts than sites, only the
    first sites get one piggybacked host each.
    """
    total_pb_hosts = perftest_mocked_dist.pb_hosts
    if total_pb_hosts >= len(mocked_remote_site_ids):
        target_site_ids = mocked_remote_site_ids
        pb_hosts_per_site = total_pb_hosts // len(mocked_remote_site_ids)
    else:
        target_site_ids = mocked_remote_site_ids[:total_pb_hosts]
        pb_hosts_per_site = 1
    with perftest_mocked_dist.distributed_piggyback_environment(
        target_site_ids=target_site_ids,
        pb_hosts_per_site=pb_hosts_per_site,
        check_shovels=False,  # shovels towards mocked sites can never run
    ):
        yield


def test_performance_bulk_change_activation_mocked_remotes(
    perftest_mocked_dist: PerformanceTest,
    mocked_remote_site_ids: list[str],
    benchmark: BenchmarkFixture,
    track_system_resources: None,
) -> None:
    """Bulk change activation against mocked remote sites, distributed piggyback disabled"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_mocked_dist.scenario_bulk_change_activation,
        args=[],
        setup=perftest_mocked_dist.setup_bulk_change_activation,
        teardown=perftest_mocked_dist.teardown_bulk_change_activation,
        rounds=perftest_mocked_dist.rounds,
        iterations=perftest_mocked_dist.iterations,
    )


def test_performance_bulk_change_activation_mocked_remotes_distributed_piggyback(
    perftest_mocked_dist: PerformanceTest,
    mocked_remote_site_ids: list[str],
    mocked_distributed_piggyback: None,
    benchmark: BenchmarkFixture,
    track_system_resources: None,
) -> None:
    """Bulk change activation against mocked remote sites, distributed piggyback enabled"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_mocked_dist.scenario_bulk_change_activation,
        args=[],
        setup=perftest_mocked_dist.setup_bulk_change_activation,
        teardown=perftest_mocked_dist.teardown_bulk_change_activation,
        rounds=perftest_mocked_dist.rounds,
        iterations=perftest_mocked_dist.iterations,
    )
