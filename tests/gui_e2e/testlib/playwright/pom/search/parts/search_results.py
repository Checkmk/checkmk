#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging

from playwright.sync_api import Locator

logger = logging.getLogger(__name__)


class SearchResults:
    """Represents the unified search results"""

    def __init__(self, locator: Locator) -> None:
        self.locator = locator

    @property
    def result_items(self) -> Locator:
        self.locator.wait_for(state="visible")
        return self.locator.get_by_role("listitem")

    def select(self, name: str) -> None:
        self.locator.get_by_role("listitem", name=name).click()
