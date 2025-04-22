#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

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

    def _get_host_link(self, host_name: str) -> Locator:
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
            self._get_host_link(host_name),
            message=f"Host '{host_name}' is not present on the 'All hosts' page",
        ).to_be_visible()
