#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import overload, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class NotificationConfiguration(CmkPage):
    """Represent the 'Notification configuration' page.

    To navigate: `Setup -> Notifications`.
    """

    page_title = "Notifications"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu("Notifications", exact=True).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?mode=notifications")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.add_notification_rule_button).to_be_visible()
        expect(self._notification_overview_header).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def delete_rule_confirmation_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Delete")

    @property
    def add_notification_rule_button(self) -> Locator:
        return self.main_area.get_suggestion("Add notification rule")

    @property
    def notification_rule_rows(self) -> Locator:
        return self.main_area.locator("table.data >> tr.data")

    @property
    def clone_and_edit_button(self) -> Locator:
        """Return locator of button to confirm the action "clone & edit" a rule.

        Apears only when a notification rule is being cloned!
        """
        return self.main_area.get_confirmation_popup_button("clone & edit")

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

    def is_the_current_page(self) -> bool:
        return (
            self.main_area.page_title_locator.is_visible()
            and self.main_area.page_title_locator.text_content() == self.page_title
        )

    def notification_rule_edit_button(self, rule_id: int | str) -> Locator:
        return self._notification_rule_row(rule_id).get_by_title("Edit this notification rule")

    def notification_rule_copy_button(self, rule_id: int | str) -> Locator:
        return self._notification_rule_row(rule_id).get_by_title(
            "Create a copy of this notification rule"
        )

    def notification_rule_delete_button(self, rule_id: int | str) -> Locator:
        return self._notification_rule_row(rule_id).get_by_title("Delete this notification rule")

    @property
    def _notification_overview_header(self) -> Locator:
        return self.main_area.locator().get_by_role("heading", name="Notification overview")

    @property
    def _notification_overview_container(self) -> Locator:
        return self.main_area.locator("div.notification-overview__container")

    def collapse_notification_overview(self, collapse: bool = True) -> None:
        container = self._notification_overview_container
        is_overview_visible = container.is_visible()
        if (collapse and is_overview_visible) or (not collapse and not is_overview_visible):
            self._notification_overview_header.locator("button").click()
            container.wait_for(state="hidden" if collapse else "visible")
        else:
            logger.info("Notification overview is already in the desired state")

    def delete_notification_rule(self, rule_id: int | str) -> None:
        self.notification_rule_delete_button(rule_id).click()
        self.delete_rule_confirmation_button.click()
        self._notification_rule_row(rule_id).wait_for(state="detached")

    def _get_notification_stat_count(self, title: str) -> Locator:
        return (
            self.main_area.locator("div.notification-stats__section")
            .filter(has=self.main_area.page.get_by_role("heading", name=title))
            .get_by_role("paragraph")
        )

    def get_total_sent_notifications_count(self) -> int:
        return int(self._get_notification_stat_count("Total sent notifications").inner_text())

    def check_total_sent_notifications_has_changed(self, previous_count: int) -> None:
        locator = self._get_notification_stat_count("Total sent notifications")
        expect(locator).not_to_have_text(re.compile(rf"^{previous_count}$"))

    def get_failed_notifications_count(self) -> int:
        return int(self._get_notification_stat_count("Failed notifications").inner_text())

    def check_failed_notifications_has_not_changed(self, previous_count: int) -> None:
        locator = self._get_notification_stat_count("Failed notifications")
        expect(locator).to_have_text(re.compile(rf"^\s{previous_count}$"))

    def rule_conditions(self, rule_number: int = 0) -> Locator:
        return self._notification_rule_row(rule_number).locator("td.rule_conditions")

    def _rule_conditions_foldable(self, rule_number: int = 0) -> Locator:
        return self.rule_conditions(rule_number).locator("div.foldable")

    def _are_rule_conditions_closed(self, rule_number: int = 0) -> bool:
        rule_conditions_foldable_class = self._rule_conditions_foldable(rule_number).get_attribute(
            "class"
        )
        if rule_conditions_foldable_class is None:
            error_message = "Rule conditions foldable has not class attribute"
            raise AttributeError(error_message)

        return "closed" in rule_conditions_foldable_class

    def _rule_conditions_foldable_header(self, rule_number: int = 0) -> Locator:
        return self._rule_conditions_foldable(rule_number).locator("div.foldable_header")

    def notification_rule_condition(self, rule_number: int, condition_name: str) -> Locator:
        return (
            self.rule_conditions(rule_number)
            .get_by_role("cell", name=condition_name)
            .locator("+ td")
        )

    def expand_conditions(self, rule_number: int = 0) -> None:
        if self._are_rule_conditions_closed(rule_number):
            self._rule_conditions_foldable_header(rule_number).click()
        else:
            logger.debug("Conditions are already expanded.")
