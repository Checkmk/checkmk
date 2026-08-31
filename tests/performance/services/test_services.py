#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: discovering the services of freshly created hosts."""

from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.perftest import PerformanceTest
from tests.performance.services import scenario
from tests.testlib.version import CMKVersion, version_from_env


@pytest.mark.skipif(
    version_from_env() < CMKVersion("2.4.0"),
    reason="Not supported on Checkmk versions below 2.4.0!",
)
@pytest.mark.usefixtures("track_system_resources")
def test_performance_services(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk service discovery"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_performance_services, perftest),
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
