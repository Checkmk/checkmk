#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class Licensing(CmkPage):
    """Represent the page `setup -> Maintenance -> Licensing`."""

    def __init__(
        self,
        page: Page,
        exists: bool = False,
        navigate_to_page: bool = True,
    ) -> None:
        self._exists = exists
        self.page_title = "Licensing"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `setup -> Hosts` page.

        This method is used within `CmkPage.__init__`.
        """
        logger.info("Navigate to 'Licensing' page")
        self.main_menu.setup_menu("Licensing").click()
        _url_pattern: str = quote_plus("wato.py?mode=licensing")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Licensing' page")
        expect(self.get_link("License usage")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def named_value(self, key: str) -> Locator:
        """The value cell shown next to the `key` header."""
        return self.main_area.locator(f'table tr:has(th:has-text("{key}"))').locator("td").first

    def get_named_value(self, key: str) -> str:
        """Read the value shown next to the `key` header."""
        value_element = self.named_value(key)
        expect(value_element, f"The '{key}' row is not shown on the licensing page").to_be_visible()
        return value_element.text_content() or ""

    def check_named_value(
        self, key: str, expected: str | re.Pattern[str], ignore_case: bool = False
    ) -> None:
        """Wait until the value shown next to the `key` header matches `expected`."""
        expect(self.named_value(key), f"Unexpected value of '{key}'").to_have_text(
            expected, ignore_case=ignore_case
        )
