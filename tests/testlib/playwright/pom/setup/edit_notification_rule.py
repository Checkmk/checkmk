#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage
from tests.testlib.playwright.pom.setup.notification_configuration import NotificationConfiguration

logger = logging.getLogger(__name__)


class EditNotificationRule(CmkPage):
    """Represent the 'Edit notification rule' page.

    To navigate: `Setup > Notifications > Edit this notification rule`.
    """

    def __init__(self, page: Page, rule_position: int = 0, navigate_to_page: bool = True) -> None:
        self.rule_position = rule_position
        self.page_title = f"Edit notification rule {rule_position}"
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        notification_configuration_page = NotificationConfiguration(self.page)
        notification_configuration_page.notification_rule_edit_button(self.rule_position).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("mode=notification_rule")), wait_until="load"
        )

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.notification_method_field).to_be_visible()
        expect(self._notify_all_contact_of_the_notified_host_or_service_checkbox).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def description_text_field(self) -> Locator:
        return self.main_area.get_input("rule_p_description")

    @property
    def notification_method_field(self) -> Locator:
        return self.main_area.locator("span[id*='rule_p_notify_plugin_sel']")

    def _checkbox_locator(self, name: str) -> Locator:
        return self.main_area.locator().get_by_role("cell", name=name).locator("label")

    @property
    def _notify_all_contact_of_the_notified_host_or_service_checkbox(self) -> Locator:
        return self._checkbox_locator("Notify all contacts of the notified host or service")

    @property
    def _the_following_users_checkbox(self) -> Locator:
        return self._checkbox_locator("The following users")

    @property
    def _add_user_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Add user")

    def user_field(self, index: int) -> Locator:
        return self.main_area.locator("span[id*='rule_p_contact_users_']").nth(index)

    def _option(self, option_name: str) -> Locator:
        return self.main_area.locator().get_by_role("option", name=option_name)

    @property
    def _match_services_checkbox(self) -> Locator:
        return self._checkbox_locator("Match services")

    def match_services_text_field(self, index: int) -> Locator:
        return self.main_area.locator(f"input[name*='rule_p_match_services_{index}']")

    def check_notify_all_contact_of_the_notified_host_or_service(self, check: bool) -> None:
        if self._notify_all_contact_of_the_notified_host_or_service_checkbox.is_checked() != check:
            self._notify_all_contact_of_the_notified_host_or_service_checkbox.click()

    def check_the_following_users(self, check: bool) -> None:
        if self._the_following_users_checkbox.is_checked() != check:
            self._the_following_users_checkbox.click()

    def check_match_services(self, check: bool) -> None:
        if self._match_services_checkbox.is_checked() != check:
            self._match_services_checkbox.click()

    def add_users(self, usernames: list[str]) -> None:
        self.check_the_following_users(True)
        for index, username in enumerate(usernames):
            self._add_user_button.click()
            self.user_field(index).click()
            self._option(username).click()

    def add_services(self, services: list[str]) -> None:
        self.check_match_services(True)
        for index, service in enumerate(services):
            self.match_services_text_field(index).fill(service)

    def modify_notification_rule(self, users: list[str] | None, services: list[str] | None) -> None:
        """Modify the default notification rule.

        Modify the default notification rule to notify the specified users and/or about the
        specified services.
        """
        if users:
            logger.info("Modify default notification rule to notify the following users: %s", users)
            self.check_notify_all_contact_of_the_notified_host_or_service(False)
            self.add_users(users)
        if services:
            logger.info(
                "Modify default notification rule to match the following services: %s", services
            )
            self.add_services(services)
        self.save_button.click()

    def restore_notification_rule(self, users: bool, services: bool) -> None:
        """Restore the default notification rule settings."""
        logger.info("Restore default notification rule settings")
        if users:
            self.check_notify_all_contact_of_the_notified_host_or_service(True)
            self.check_the_following_users(False)
        if services:
            self.check_match_services(False)
        self.save_button.click()
