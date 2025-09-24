#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This test module verifies the activating of pending changes through the "Changes" slideout
of main menu.
"""

import logging

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.search.unified_search import UnifiedSearchSlideout
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


def test_unified_search_slideout(dashboard_page: MainDashboard, test_site: Site) -> None:
    """Check elements of 'Unified Search' slideout"""
    logger.info("Init unified search slideout")
    search = UnifiedSearchSlideout(dashboard_page)

    logger.info("Validate provider select functionality")
    search.provider_select.select("Monitoring")
    assert search.provider_select.value() == "Monitoring"

    logger.info("Validate serarch operator select functionality")
    search.search_operator_select.select("hg:")
    assert search.input.input_value() == "hg:"

    search.provider_select.select("Setup")
    logger.info("Execute simple search and validate that results are shown")
    results = search.exec_search("notification")
    expect(results.locator).to_be_visible()
    assert results.get_results.count() > 0
