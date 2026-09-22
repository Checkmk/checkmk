#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AllHosts(CmkPage):
    """Represents page `Monitor -> Overview -> All hosts`"""

    page_title: str = "All hosts"

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Monitor -> Overview -> All hosts` page."""
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.monitor_all_hosts.click()
        self.page.wait_for_url(url=re.compile(quote_plus("view_name=allhost")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def try_the_new_view(self) -> Locator:
        """The button offering the Vue "All hosts" page.

        Rendered by the `cmk-monitoring-page-link-button` web component and
        teleported out of the app root, so it is looked up from the main area
        rather than from the app, and never from the page: a site still serving
        its content in the main iframe keeps it out of the top-level document.
        """
        return self.main_area.locator("button.monitoring-page-link-button")

    @property
    def page_menu_shortcuts(self) -> Locator:
        """The shortcut area of the page menu bar.

        Where the cloud edition teleports the switch button, because its licensing
        banner covers the page state area the other editions use.
        """
        return self.main_area.locator("#page_menu_bar .shortcuts")

    @property
    def try_the_new_view_in_page_menu(self) -> Locator:
        """The switch button as mounted inside the page menu bar's shortcut area."""
        return self.page_menu_shortcuts.locator("button.monitoring-page-link-button")

    @property
    def return_to_classic_view(self) -> Locator:
        """The "Return to classic view" button the new Vue page renders.

        Teleported into the title bar, not into the shortcut area: 2.5.0 moves
        only the way over, so this one still sits where the licensing banner is.
        """
        return self.main_area.locator("button.monitoring-all-hosts-app__legacy-view-button")

    def get_host_link(self, host_name: str) -> Locator:
        """Get the link to a host in the 'All hosts' view.

        Args:
            host_name: The name of the host to get the link for.
        """
        return self.main_area.locator("table.data").get_by_role("link", name=host_name)

    def check_host_is_present(self, host_name: str) -> None:
        """Check if a host is present in the 'All hosts' view.

        Args:
            host_name: The name of the host to check.
        """
        logger.info("Check if host '%s' is present", host_name)
        expect(
            self.get_host_link(host_name),
            message=f"Host '{host_name}' is not present on the 'All hosts' page",
        ).to_be_visible()
