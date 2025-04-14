#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from urllib.parse import quote_plus

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class GlobalSettings(CmkPage):
    page_title: str = "Global settings"
    dropdown_buttons: list[str] = ["Related", "Display", "Help"]

    def navigate(self) -> None:
        logger.info("Navigate to 'Global settings' page")
        _url_pattern = quote_plus("wato.py?mode=globalvars")
        self.main_menu.setup_menu(self.page_title).click()
        self.page.wait_for_url(re.compile(f"{_url_pattern}$"), wait_until="load")

    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Global settings' page")
        self.main_area.check_page_title(self.page_title)

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def _searchbar(self) -> Locator:
        return self.main_area.locator().get_by_role(role="textbox", name="Find on this page ...")

    def setting_link(self, setting_name: str) -> Locator:
        return self.get_link(setting_name)

    def search_settings(self, search_text: str) -> None:
        """Search for a setting using the searchbar."""
        logger.info("Search for setting: %s", search_text)
        self._searchbar.fill(search_text)
        self.main_area.locator().get_by_role(role="button", name="Submit").click()
