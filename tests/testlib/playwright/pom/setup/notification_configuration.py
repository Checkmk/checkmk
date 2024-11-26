#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import overload
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class NotificationConfiguration(CmkPage):
    """Represent the 'Notification configuration' page.

    To navigate: `Setup -> Notifications`.
    """

    page_title = "Notifications"

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
    def delete_rule_confirmation_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Delete")

    @property
    def add_notification_rule_button(self) -> Locator:
        return self.main_area.get_suggestion("Add notification rule")

    @overload
    def _notification_rule_row(self, rule_id: str) -> Locator: ...

    @overload
    def _notification_rule_row(self, rule_id: int) -> Locator: ...

    def _notification_rule_row(self, rule_id: str | int) -> Locator:
        """Return a locator for the specific notification rule row.

        The rule can be identified by rule position, providing an integer input for this function
        or by rule description, providing a string input for this function.
        """
        if isinstance(rule_id, str):
            rule_row_locator = self.main_area.locator(
                f"table[class*='data'] >> tr:has(td:text-is('{rule_id}'))"
            )
        elif isinstance(rule_id, int):
            rule_row_locator = self.main_area.locator(
                f"tr[class*='data']:has(td[class*='narrow']:text-is('{rule_id}'))"
            )
        else:
            raise TypeError(
                f"Unsupported rule_id type: {type(rule_id)}",
                "Expected 'str' (rule description) or 'int' (rule position)!",
            )
        return rule_row_locator

    def notification_rule_edit_button(self, rule_id: int | str) -> Locator:
        return self._notification_rule_row(rule_id).get_by_title("Edit this notification rule")

    def notification_rule_copy_button(self, rule_id: int | str) -> Locator:
        return self._notification_rule_row(rule_id).get_by_title(
            "Create a copy of this notification rule"
        )

    def notification_rule_delete_button(self, rule_id: int | str) -> Locator:
        return self._notification_rule_row(rule_id).get_by_title("Delete this notification rule")

    def notification_overview_container(self) -> Locator:
        return self.main_area.locator("div[class='overview_container']")

    def collapse_notification_overview(self, collapse: bool = True) -> None:
        is_overview_visible = self.notification_overview_container().is_visible()
        if (collapse and is_overview_visible) or (not collapse and not is_overview_visible):
            self.main_area.locator().get_by_role("heading", name="Notification overview").locator(
                "button"
            ).click()
        else:
            logger.info("Notification overview is already in the desired state")

    def delete_notification_rule(self, rule_id: int | str) -> None:
        self.notification_rule_delete_button(rule_id).click()
        self.delete_rule_confirmation_button.click()
