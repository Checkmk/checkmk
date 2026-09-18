#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: hosts the Dynamic host configuration creates from piggyback data."""

from collections.abc import Iterator
from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.dcd import scenario
from tests.performance.perftest import PerformanceTest


@pytest.fixture(name="dcd_piggyback_env", scope="function")
def _dcd_piggyback_env(perftest: PerformanceTest) -> Iterator[None]:
    """Provide the (un-timed) DCD piggyback environment for the measured scenario."""
    try:
        scenario.setup_dcd_piggyback_env(perftest)
        yield
    finally:
        # teardown is idempotent (every deletion is existence-guarded, delete_file uses
        # `rm -f`), so it also cleans up after a setup that failed part-way through.
        scenario.teardown_dcd_piggyback_env(perftest)


@pytest.mark.usefixtures("dcd_piggyback_env", "track_system_resources")
def test_performance_piggyback(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """DCD piggyback host discovery

    Measure forced DCD cycle that creates and discovers pre-staged piggyback hosts.
    """
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_performance_dcd_piggyback, perftest),
        setup=partial(scenario.setup_dcd_piggyback_round, perftest),
        teardown=partial(scenario.teardown_dcd_piggyback_round, perftest),
        rounds=perftest.rounds,
        # The first forced DCD cycle after site/daemon start is always cold; warm up at
        # least once so that one-off cost is excluded from the measured rounds.
        warmup_rounds=max(1, perftest.warmup_rounds),
        # pytest-benchmark forbids iterations > 1 together with a `setup` function, so this
        # must stay 1; per-round work is repeated via `rounds`, not `iterations`.
        iterations=1,
    )
