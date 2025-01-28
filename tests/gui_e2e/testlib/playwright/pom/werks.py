#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class Werks(CmkPage):
    page_title: str = "Change log (Werks)"
    dropdown_buttons: list[str] = ["Werks", "Display", "Help"]

    def navigate(self) -> None:
        logger.info("Navigate to 'Werks' page")
        self.main_menu.help_werks.click()
        self.page.wait_for_url(url=re.compile("change_log.py$"), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is 'Werks' page")
        self.main_area.check_page_title(self.page_title)

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def get_recent_werks(self, count: int = 100) -> dict[int, str]:
        """Group werks by `Day of creation` using the filter mechanism."""
        logger.info("Filter werks by 'Day of creation' and get the recent %d werks", count)
        self.get_link("Filter").click()
        filter_popup = self.main_area.locator("#popup_filters")
        filter_popup.locator("#wo_grouping").select_option(label="Day of creation")
        self.click_and_wait(self.apply_filter, navigate=True)

        links = self.main_area.locator("a").get_by_text("#").element_handles()[:count]
        werks = {
            int(str(link.text_content())[1:]): str(link.get_attribute("href")) for link in links
        }

        return werks

    @property
    def apply_filter(self) -> Locator:
        return self.main_area.locator().get_by_role(role="button", name="Apply")

    @property
    def reset_filter(self) -> Locator:
        return self.main_area.locator().get_by_role(role="button", name="Reset")

    def werk(self, werk_id: int) -> Locator:
        return self.get_link(f"#{werk_id}")
