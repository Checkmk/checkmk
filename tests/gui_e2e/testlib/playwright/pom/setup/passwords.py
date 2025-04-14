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


class Passwords(CmkPage):
    """Represent the page 'Passwords', which lists the stored passwords.

    Accessible at,
    Setup > General > Passwords
    """

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Passwords' page")
        self.main_menu.setup_menu("Passwords").click()
        self.page.wait_for_url(url=re.compile(quote_plus("mode=passwords")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Passwords' page")
        self.main_area.check_page_title("Passwords")
        expect(self.add_password_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_password_button(self) -> Locator:
        return self.main_area.get_suggestion("Add password")

    def _password_row(self, title_or_id: str) -> Locator:
        main_locator = self.main_area.locator()
        cell = main_locator.get_by_role("cell", name=title_or_id)
        return main_locator.get_by_role("row").filter(has=cell)

    def password_source(self, title_or_id: str) -> Locator:
        """Get a locator to the 'Source' column of a password row.

        The source column contains for example a link to the Quick Setup which created the password.
        """
        return self._password_row(title_or_id).locator("td[class*='source']")
