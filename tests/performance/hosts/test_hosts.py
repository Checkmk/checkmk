#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: creating and deleting hosts in bulk."""

from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.hosts import scenario
from tests.performance.perftest import PerformanceTest


def test_performance_hosts_restart(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk host creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_create_and_delete_hosts, perftest),
        args=[
            perftest.rounds * perftest.iterations
        ],  # pass the iterations to switch to restart mode
        rounds=1,  # run a single time
        iterations=1,  # run a single time
    )


@pytest.mark.usefixtures("track_system_resources")
def test_performance_hosts(perftest_dist: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk host creation across a distributed setup"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_create_and_delete_hosts, perftest_dist),
        args=[],
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )
