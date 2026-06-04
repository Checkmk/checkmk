#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Performance test: Distributed site

To run this test with all reporting enabled, use the following command:

$ pytest tests/performance --html=performance.htm --self-contained-html --ignore-running-procs
  --benchmark-json="benchmark.json" --benchmark-save-data --benchmark-name=long --benchmark-verbose
  --log-cli-level=INFO

For more details, see pytest --help the documentation of pytest-benchmark.
"""

import logging
from collections.abc import Iterator

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.perftest import PerformanceTest
from tests.testlib.common.repo import qa_test_data_path
from tests.testlib.site import Site
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger(__name__)

dump_path_repo = qa_test_data_path() / "plugins_integration/dumps/piggyback"


@pytest.fixture(name="perftest_dist", scope="module")
def _perftest_dist(
    central_site: Site, remote_site: Site, remote_site_2: Site, pytestconfig: pytest.Config
) -> Iterator[PerformanceTest]:
    """Distributed performance test with 2 remote sites"""
    yield PerformanceTest(
        central_site, remote_sites=[remote_site, remote_site_2], pytestconfig=pytestconfig
    )


def test_performance_hosts(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    """Bulk host creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_dist.scenario_create_and_delete_hosts,
        args=[],
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )


def test_performance_bulk_change_activation(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    """Bulk host creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_dist.scenario_bulk_change_activation,
        args=[],
        setup=perftest_dist.setup_bulk_change_activation,
        teardown=perftest_dist.teardown_bulk_change_activation,
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )


@pytest.fixture(name="distributed_piggyback", scope="module")
def _distributed_piggyback(perftest_dist: PerformanceTest) -> Iterator[None]:
    """Enable the piggyback hub on all sites and create piggybacked hosts on the remote sites."""
    with perftest_dist.distributed_piggyback_environment():
        yield


@pytest.mark.skipif(
    version_from_env() < CMKVersion("2.4.0"),
    reason="Distributed piggyback is not supported on Checkmk versions below 2.4.0!",
)
def test_performance_bulk_change_activation_distributed_piggyback(
    perftest_dist: PerformanceTest,
    distributed_piggyback: None,
    benchmark: BenchmarkFixture,
    track_system_resources: None,
) -> None:
    """Bulk change activation with distributed piggyback enabled (CMK-35259)

    Activate a large number of pending changes in a distributed environment
    where the piggyback hub is enabled on all sites and a notable amount of
    piggybacked hosts is monitored on the remote sites.
    """
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_dist.scenario_bulk_change_activation,
        args=[],
        setup=perftest_dist.setup_bulk_change_activation,
        teardown=perftest_dist.teardown_bulk_change_activation,
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )
