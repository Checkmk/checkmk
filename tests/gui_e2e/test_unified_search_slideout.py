#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This test module verifies the activating of pending changes through the "Changes" slideout
of main menu.
"""

import logging
from typing import Literal

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.search.unified_search import UnifiedSearchSlideout

logger = logging.getLogger(__name__)


def test_unified_search_slideout(dashboard_page: MainDashboard) -> None:
    """Check elements of 'Unified Search' slideout"""
    logger.info("Init unified search slideout")
    search = UnifiedSearchSlideout(dashboard_page)

    logger.info("Validate provider select functionality")
    provider_name: Literal["Monitoring"] = "Monitoring"
    search.provider_select.select(provider_name)
    expect(
        search.provider_select.button,
        message=(
            "Provider select button text is incorrect."
            f" Expected '{provider_name}'; got '{search.provider_select.button_text}'."
        ),
    ).to_have_text(provider_name)

    logger.info("Validate search operator select functionality")
    search_operator: Literal["hg:"] = "hg:"
    search.search_operator_select.select(search_operator)
    expect(
        search.input,
        message=(
            "Search input value is incorrect."
            f" Expected '{search_operator}'; got '{search.input.input_value()}'."
        ),
    ).to_have_value(search_operator)
    search.input.clear()

    logger.info("Execute simple search and validate that results are shown")
    search.provider_select.select("Setup")
    results = search.exec_search("notification")
    expect(
        results.result_items.first, message="Search result items are not visible"
    ).to_be_visible()
