#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.pom.search.parts.search_results import SearchResults

logger = logging.getLogger(__name__)


class RecentlyResults(SearchResults):
    """Represents the unified search recently results"""

    def __init__(self, locator: Locator) -> None:
        self.locator = locator

    @property
    def clear_all_button(self) -> Locator:
        return self.locator.get_by_role("button", name="Clear all")

    def clear_all(self) -> None:
        self.clear_all_button.click()
