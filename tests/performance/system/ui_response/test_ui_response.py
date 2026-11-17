#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: how long a page of the GUI takes to load."""

from functools import partial

import pytest
from playwright.sync_api import BrowserContext
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.system.perftest import PerformanceTest
from tests.performance.system.ui_response import scenario
from tests.performance.system.ui_response.scenario import CmkPageUrl

#: Deliberately loose. These are the first figures anyone has for the monitoring pages, and
#: the first runs are for learning what they are rather than policing a threshold nobody has
#: agreed. Tighten once a baseline exists.
MONITORING_PAGE_MAX_SECONDS = 30.0


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
        # The classic view, measured the same way so it can be compared with the new pages of
        # later branches. A classic view is server-rendered, so its table is in the document
        # and `domcontentloaded` is the whole story.
        CmkPageUrl(
            "view_all_hosts",
            "view.py?view_name=allhosts",
            max_average_duration=MONITORING_PAGE_MAX_SECONDS,
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
    print(f"Checking {page_url.value}...")  # It's OK for test/script helpers to print()
    benchmark.pedantic(
        partial(scenario.scenario_performance_ui_response, perftest),
        args=[context, page_url],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
