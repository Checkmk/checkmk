#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from abc import abstractmethod
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.setup.notification_configuration import (
    NotificationConfiguration,
)
from tests.gui_e2e.testlib.playwright.pom.setup.quick_setup import QuickSetupPage

logger = logging.getLogger(__name__)


STAGE_TRIGGERING_EVENTS = "Triggering Content"
STAGE_FILTER_HOSTS_SERVICES = "Filter for hosts/services"
STAGE_NOTIFICATION_METHOD = "Notification method (plug-in)"
STAGE_RECIPIENT = "Recipient"
STAGE_SENDING_CONDITIONS = "Sending conditions"
STAGE_GENERAL_PROPERTIES = "General properties"

HOST_FILTERS = "Host filters"


class BaseNotificationPage(QuickSetupPage):
    """Base class for Notification Quick Setup pages."""

    page_title = ""

    @abstractmethod
    def navigate(self) -> None:
        pass

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.overview_mode_button).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _get_row(self, row_name: str) -> Locator:
        return self.main_area.locator(
            f'table[class*="form-dictionary"] >> tr:has(span:text-is("{row_name}"))'
        )

    # stage 1
    @property
    def host_events_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Host events")

    @property
    def _host_events_rows(self) -> Locator:
        return self._get_row("Host events").locator("table > tr")

    @property
    def _service_events_rows(self) -> Locator:
        return self._get_row("Service events").locator("table > tr")

    @property
    def _add_service_event_button(self) -> Locator:
        return self._get_row("Service events").get_by_role("button", name="Add event")

    def _service_event_dropdown(self, index: int = 0) -> Locator:
        return self._service_events_rows.nth(index).get_by_role("combobox").nth(0)

    def _service_event_row_dropdown_option(self, option: str, index: int = 0) -> Locator:
        return self._service_events_rows.nth(index).get_by_role("option", name=option)

    def _service_event_first_dropdown(self, index: int = 0) -> Locator:
        return self._service_events_rows.nth(index).get_by_role("combobox").nth(1)

    def _service_event_second_dropdown(self, index: int = 0) -> Locator:
        return self._service_events_rows.nth(index).get_by_role("combobox").nth(2)

    # stage 2
    @property
    def _host_filters_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Host filters")

    @property
    def hosts_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Hosts", exact=True)

    @property
    def hosts_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Hosts").locator("input")

    @property
    def _service_filters_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Service filters")

    @property
    def _exclude_services_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Exclude services")

    @property
    def services_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Services", exact=True)

    def _match_services_text_field(self, index: int = 0) -> Locator:
        return self._get_row("Services").locator("input").nth(index)

    # stage 3
    @property
    def stage_three_locator(self) -> Locator:
        return self.main_area.locator("li").filter(has_text="Notification method (plug-in)")

    @property
    def select_email_parameter_dropdown(self) -> Locator:
        return self.stage_three_locator.get_by_role("combobox").nth(1)

    def notification_method_option(self, option: str) -> Locator:
        return self.stage_three_locator.get_by_role("option", name=option)

    def create_parameter_button(self) -> Locator:
        return self.stage_three_locator.get_by_role("button", name="Create")

    # stage 4
    @property
    def _stage_four_locator(self) -> Locator:
        return self.main_area.locator("li").filter(has_text="Recipient")

    @property
    def _add_recipient_button(self) -> Locator:
        return self._stage_four_locator.get_by_role("button", name="Add recipient")

    @property
    def _recipients_rows(self) -> Locator:
        return self._stage_four_locator.get_by_label("Select recipient").locator("table > tr")

    def delete_recipient_button(self, index: int = 0) -> Locator:
        return self._recipients_rows.nth(index).get_by_role("button").nth(0)

    def select_recipient_dropdown(self, index: int = 0) -> Locator:
        return self._recipients_rows.nth(index).get_by_role("combobox").nth(0)

    def select_recipient_option(self, index: int, option: str) -> Locator:
        return self._recipients_rows.nth(index).get_by_role("option", name=option)

    def add_new_entry_button(self, index: int = 0) -> Locator:
        return self._recipients_rows.nth(index).get_by_role("button", name="Add new entry")

    def recipient_first_dropdown(self, index: int = 0) -> Locator:
        return self._recipients_rows.nth(index).get_by_role("combobox").nth(1)

    @property
    def apply_and_create_another_rule_button(self) -> Locator:
        return self.main_area.locator().get_by_text("Apply & create another rule")

    def delete_all_service_events(self) -> None:
        for _ in self._service_events_rows.all():
            self._service_events_rows.nth(0).get_by_role("button").click()

    # stage 6
    @property
    def description_text_field(self) -> Locator:
        return self.main_area.locator().get_by_label("Description").get_by_role("textbox")

    @property
    def _disable_rule_button(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Disable rule")

    def add_service_event(
        self,
        index: int,
        service_event_name: str,
        first_option: str | None = None,
        second_option: str | None = None,
    ) -> None:
        self._add_service_event_button.click()
        self._service_event_dropdown(index).click()
        self._service_event_row_dropdown_option(service_event_name, index).click()
        if first_option:
            self._service_event_first_dropdown(index).click()
            self._service_event_row_dropdown_option(first_option, index).click()
        if second_option:
            self._service_event_second_dropdown(index).click()
            self._service_event_row_dropdown_option(second_option, index).click()

    def expand_host_filters(self) -> None:
        if self.hosts_checkbox.is_hidden():
            self._host_filters_button.click()

    def expand_service_filters(self) -> None:
        if self.services_checkbox.is_hidden():
            self._service_filters_button.click()
        # The scrollbar interrupts the interaction with services checkbox -> scroll into view
        self._exclude_services_checkbox.scroll_into_view_if_needed()

    def apply_services_filter(self, service_name: str) -> None:
        self.expand_service_filters()
        self.services_checkbox.set_checked(True)
        self._match_services_text_field(0).fill(service_name)

    def delete_all_recipients(self) -> None:
        for _ in self._recipients_rows.all():
            self.delete_recipient_button(0).click()

    def set_recipient(self, index: int, recipient_option_name: str) -> None:
        self.select_recipient_dropdown(index).click()
        self.select_recipient_option(index, recipient_option_name).click()

    def add_recipient(
        self, index: int, recipient_option_name: str, recipient_value: str | None = None
    ) -> None:
        self._add_recipient_button.click()
        self.select_recipient_dropdown(index).click()
        self.select_recipient_option(index, recipient_option_name).click()
        if recipient_value:
            self.add_new_entry_button(index).click()
            self.recipient_first_dropdown(index).click()
            self.select_recipient_option(index, recipient_value).click()

    def check_disable_rule(self, disable: bool) -> None:
        if self._disable_rule_button.is_checked() != disable:
            self._disable_rule_button.click()

    # This should be part of the test itself, not of the BaseNotificationPage
    def modify_notification_rule(self, user: str, service: str, description: str) -> None:
        """Modify the default notification rule.

        Modify the default notification rule to notify the specified user and about the
        specified service.
        """
        logger.info("Switch to the overview mode")
        self.overview_mode_button.click()

        logger.info("Disable host events filter")
        self.host_events_checkbox.set_checked(False)

        logger.info("Add status event filter: status changes from ANY to WARN")
        self.delete_all_service_events()
        self.add_service_event(0, "Status change", "Any", "WARN")

        logger.info("Apply service filter: '%s'", service)
        self.apply_services_filter(service)

        logger.info("Select default email parameter")
        self.select_email_parameter_dropdown.click()
        self.notification_method_option("Default").click()

        logger.info("Add recipient: '%s'", user)
        self.delete_all_recipients()
        self.add_recipient(0, "Specific users", user)

        logger.info("Add description: '%s'", description)
        self.description_text_field.fill(description)

        logger.info("Save the changes")
        self.apply_and_create_another_rule_button.click()


class EditNotificationRule(BaseNotificationPage):
    """Represent the 'Edit notification rule' page.

    To navigate: `Setup > Notifications > Edit this notification rule`.
    """

    def __init__(self, page: Page, rule_position: int = 0, navigate_to_page: bool = True) -> None:
        self.rule_position = rule_position
        self.page_title = f"Edit notification rule {rule_position}"
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        notification_configuration_page = NotificationConfiguration(self.page)
        # The scrollbar interrupts the interaction with rule edit button -> -> collapse overview
        notification_configuration_page.collapse_notification_overview(True)
        notification_configuration_page.notification_rule_edit_button(self.rule_position).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("mode=notification_rule_quick_setup")), wait_until="load"
        )
        self._validate_page()


class AddNotificationRule(BaseNotificationPage):
    """Represent the 'Add notification rule' page.

    To navigate: `Setup > Notifications > Add notification rule`.
    """

    page_title = "Add notification rule"

    def navigate(self) -> None:
        notification_configuration_page = NotificationConfiguration(self.page)
        notification_configuration_page.add_notification_rule_button.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("mode=notification_rule_quick_setup")), wait_until="load"
        )
        self._validate_page()

    @property
    def si_description(self) -> Locator:
        return self.editor_slide_in.locator("td.value").first.locator("input")

    @property
    def si_custom_sender_checkbox(self) -> Locator:
        return self.editor_slide_in.get_by_role("checkbox", name='Custom sender ("From")')

    @property
    def si_displayname_checkbox(self) -> Locator:
        return self.editor_slide_in.get_by_role("checkbox", name="Display name")

    @property
    def si_displayname_input(self) -> Locator:
        return self.editor_slide_in.get_by_label("Display name").locator("input")

    @property
    def si_service_subject_checkbox(self) -> Locator:
        return self.editor_slide_in.get_by_role(
            "checkbox", name="Subject line for service notifications"
        )

    @property
    def si_service_subject_input(self) -> Locator:
        return self.editor_slide_in.get_by_label("Subject line for service notifications").locator(
            "input"
        )

    @property
    def si_host_subject_checkbox(self) -> Locator:
        return self.editor_slide_in.get_by_role(
            "checkbox", name="Subject line for host notifications"
        )

    @property
    def si_host_subject_input(self) -> Locator:
        return self.editor_slide_in.get_by_label("Subject line for host notifications").locator(
            "input"
        )
