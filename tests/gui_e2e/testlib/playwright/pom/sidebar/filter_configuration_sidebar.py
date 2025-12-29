#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.pom.sidebar.base_sidebar import SidebarHelper


class FilterConfigurationSidebar(SidebarHelper):
    """Class that represents the sidebar to filter a dashboard.

    To navigate: '{within any dasboard} > Filter'.
    """

    sidebar_title = "Filter configuration"

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name="Dashboard filter")

    @property
    @override
    def sidebar_title_locator(self) -> Locator:
        """Locator property for the sidebar title."""
        return self.locator().get_by_text(self.sidebar_title)

    @property
    def close_filter_configuration_button(self) -> Locator:
        """Locator property for the button to close the filter configuration."""
        return self.locator().get_by_role("button", name="Close filter configuration")
