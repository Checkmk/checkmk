#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import override

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AddSidebarElement(CmkPage):
    """Represents the 'Add sidebar element' page in the GUI.

    This page is accessible via the navigation path:
    Sidebar -> 'Add elements to your sidebar' button.
    """

    page_title: str = "Add sidebar element"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Add sidebar element' page")
        self.sidebar.locator("div#add_snapin > a").click()

    @override
    def validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def snapin_container(self, snapin_id: str) -> Locator:
        """Returns the container element for the snapin that can be added to the sidebar.

        Args:
            snapin_id: The ID of the snapin.

        Returns:
            The locator for the snapin container in "Add sidebar element" page.
        """
        return self.main_area.locator(f"div#{snapin_id}")

    def add_snapin_to_sidebar(self, snapin_id: str) -> None:
        """Add a snapin to the sidebar and wait for it to be detached.

        Args:
            snapin_id: The ID of the snapin to add.
        """
        snapin_container = self.snapin_container(snapin_id)
        self.main_area.locator("div.snapinadder").filter(has=snapin_container).click()
        snapin_container.wait_for(state="detached")
