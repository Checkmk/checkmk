#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Performance: activating a configuration change across a distributed setup."""

from collections.abc import Iterator
from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.activation import scenario
from tests.performance.perftest import PerformanceTest
from tests.testlib.version import CMKVersion, version_from_env


@pytest.mark.usefixtures("track_system_resources")
def test_performance_bulk_change_activation(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture
) -> None:
    """Bulk change activation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_bulk_change_activation, perftest_dist),
        args=[],
        setup=partial(scenario.setup_bulk_change_activation, perftest_dist),
        teardown=partial(scenario.teardown_bulk_change_activation, perftest_dist),
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
@pytest.mark.usefixtures("distributed_piggyback", "track_system_resources")
def test_performance_bulk_change_activation_distributed_piggyback(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture
) -> None:
    """Bulk change activation with distributed piggyback enabled (CMK-35259)

    Activate a large number of pending changes in a distributed environment
    where the piggyback hub is enabled on all sites and a notable amount of
    piggybacked hosts is monitored on the remote sites.
    """
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_bulk_change_activation, perftest_dist),
        args=[],
        setup=partial(scenario.setup_bulk_change_activation, perftest_dist),
        teardown=partial(scenario.teardown_bulk_change_activation, perftest_dist),
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )
