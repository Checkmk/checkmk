#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Performance: activating a configuration change across a distributed setup."""

from functools import partial

from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.system.activation import scenario
from tests.performance.system.perftest import PerformanceTest


def test_performance_bulk_change_activation(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    """Bulk change activation"""
    benchmark.pedantic(
        partial(scenario.scenario_bulk_change_activation, perftest_dist),
        args=[],
        setup=partial(scenario.setup_bulk_change_activation, perftest_dist),
        teardown=partial(scenario.teardown_bulk_change_activation, perftest_dist),
        # A round costs over a minute of untimed setup and teardown, and 8 rounds keep the
        # mean as steady from night to night as 16 did.
        rounds=perftest_dist.rounds_or(8),
    )
