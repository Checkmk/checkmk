#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from typing import Literal

from playwright.sync_api import Locator

logger = logging.getLogger(__name__)


class ProviderSelect:
    """Represents the unified search provider select (independent filter buttons)"""

    def __init__(self, locator: Locator) -> None:
        self.locator = locator

    def get_button(
        self, provider_name: Literal["All", "Monitoring", "Customize", "Setup"]
    ) -> Locator:
        """Get the button for a specific provider."""
        return self.locator.get_by_role("button", name=provider_name)

    def is_active(self, provider_name: Literal["All", "Monitoring", "Customize", "Setup"]) -> bool:
        """Check if a specific provider button is active."""
        button = self.get_button(provider_name)
        # Check for the active class on the button element
        class_attr = button.get_attribute("class") or ""
        return "unified-search-filter-button--active" in class_attr

    def select(self, provider_name: Literal["All", "Monitoring", "Customize", "Setup"]) -> None:
        """Click the button for a specific provider."""
        self.get_button(provider_name).click()
