#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: how long a page of the GUI takes to load."""

from functools import partial

import pytest
from playwright.sync_api import BrowserContext
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.perftest import PerformanceTest
from tests.performance.ui_response import scenario
from tests.performance.ui_response.scenario import CmkPageUrl


@pytest.mark.parametrize(
    "page_url",
    [
        CmkPageUrl("login", "login.py", login=False),
        CmkPageUrl("edit_host", "wato.py?folder={folder}&host={host}&mode=edit_host"),
        CmkPageUrl("service_discovery", "wato.py?folder={folder}&host={host}&mode=inventory"),
        CmkPageUrl(
            "host_parameters",
            "wato.py?folder={folder}&host={host}&mode=object_parameters",
        ),
    ],
    ids=lambda url: url.id,
)
@pytest.mark.usefixtures("track_system_resources")
def test_performance_ui_response(
    perftest: PerformanceTest,
    benchmark: BenchmarkFixture,
    page_url: CmkPageUrl,
    context: BrowserContext,
) -> None:
    print(f"Checking {page_url.value}...")  # noqa: T201  # It's OK for test/script helpers to print()
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_performance_ui_response, perftest),
        args=[context, page_url],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
