#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: importing every agent-based check plugin into the Nagios core."""

import logging
from collections.abc import Iterator
from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.nagios import scenario
from tests.performance.perftest import PerformanceTest

logger = logging.getLogger(__name__)


@pytest.fixture(name="perftest_nagios", scope="function")
def _perftest_nagios(perftest: PerformanceTest) -> Iterator[PerformanceTest]:
    site = perftest.central_site
    nagios_core = "nagios"
    cmc_core = "cmc"

    logger.info("Switching core to %s", nagios_core)
    site.stop()
    site.omd("config", "set", "CORE", nagios_core, check=True)
    p = site.omd("config", "show", "CORE", check=True)
    assert p.stdout.strip() == nagios_core
    site.start()

    yield perftest

    logger.info("Switching core back to %s", cmc_core)
    site.stop()
    site.omd("config", "set", "CORE", cmc_core, check=True)
    p = site.omd("config", "show", "CORE", check=True)
    assert p.stdout.strip() == cmc_core
    site.start()


def test_nagios_core_plugin_import(
    perftest_nagios: PerformanceTest, benchmark: BenchmarkFixture
) -> None:
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_nagios_core_plugin_import, perftest_nagios),
        args=[perftest_nagios.rounds * perftest_nagios.iterations],
        setup=partial(scenario.setup_nagios_core_plugin_import, perftest_nagios),
        rounds=1,  # run a single time
        iterations=1,  # run a single time
    )
