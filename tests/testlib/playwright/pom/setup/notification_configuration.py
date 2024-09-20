#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class NotificationConfiguration(CmkPage):
    """Represent the 'Notification configuration' page.

    To navigate: `Setup -> Notifications`.
    """

    page_title = "Notification configuration"

    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu("Notifications", exact=True).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?mode=notifications")), wait_until="load"
        )
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.add_notification_rule_button).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_notification_rule_button(self) -> Locator:
        return self.main_area.get_suggestion("Add notification rule")

    def _notification_rule_row(self, row_number: int) -> Locator:
        return self.main_area.locator(
            f"tr[class*='data']:has(td[class*='narrow']:text-is('{row_number}'))"
        )

    def notification_rule_edit_button(self, row_number: int) -> Locator:
        return self._notification_rule_row(row_number).get_by_title("Edit this notification rule")
