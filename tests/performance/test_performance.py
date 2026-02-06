#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Performance test: Single site

To run this test with all reporting enabled, use the following command:

$ pytest tests/performance --html=performance.htm --self-contained-html --ignore-running-procs
  --benchmark-json="benchmark.json" --benchmark-save-data --benchmark-name=long --benchmark-verbose
  --log-cli-level=INFO

For more details, see pytest --help the documentation of pytest-benchmark.
"""

import logging
from collections.abc import Iterator

import pytest
from playwright.sync_api import BrowserContext
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.perftest import CmkPageUrl, PerformanceTest
from tests.testlib.site import Site
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger(__name__)


@pytest.fixture(name="perftest", scope="module")
def _perftest(single_site: Site, pytestconfig: pytest.Config) -> Iterator[PerformanceTest]:
    """Single-site performance test"""
    yield PerformanceTest(single_site, remote_sites=None, pytestconfig=pytestconfig)


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


def test_performance_hosts_restart(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk host creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_create_and_delete_hosts,
        args=[
            perftest.rounds * perftest.iterations
        ],  # pass the iterations to switch to restart mode
        rounds=1,  # run a single time
        iterations=1,  # run a single time
    )


@pytest.mark.skipif(
    version_from_env() < CMKVersion("2.4.0"),
    reason="Not supported on Checkmk versions below 2.4.0!",
)
def test_performance_services(
    perftest: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    """Bulk service discovery"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_performance_services,
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )


@pytest.mark.skip("CMK-27171: Unstable scenario; fix in progress")
def test_performance_piggyback(
    perftest: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_performance_dcd_piggyback,
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )


@pytest.mark.parametrize(
    "page_url",
    [
        CmkPageUrl("login", "login.py", login=False, max_average_duration=0.3),
        CmkPageUrl("edit_host", "wato.py?folder={folder}&host={host}&mode=edit_host"),
        CmkPageUrl("service_discovery", "wato.py?folder={folder}&host={host}&mode=inventory"),
        CmkPageUrl(
            "host_parameters",
            "wato.py?folder={folder}&host={host}&mode=object_parameters",
            max_average_duration=2.0,
            request_timeout=3,
        ),
    ],
    ids=lambda url: url.id,
)
def test_performance_ui_response(
    perftest: PerformanceTest,
    benchmark: BenchmarkFixture,
    track_system_resources: None,
    page_url: CmkPageUrl,
    context: BrowserContext,
) -> None:
    print(f"Checking {page_url.value}...")
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_performance_ui_response,
        args=[context, page_url],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )


def test_nagios_core_plugin_import(
    perftest_nagios: PerformanceTest, benchmark: BenchmarkFixture
) -> None:
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_nagios.scenario_nagios_core_plugin_import,
        args=[perftest_nagios.rounds * perftest_nagios.iterations],
        setup=perftest_nagios.setup_nagios_core_plugin_import,
        rounds=1,  # run a single time
        iterations=1,  # run a single time
    )
