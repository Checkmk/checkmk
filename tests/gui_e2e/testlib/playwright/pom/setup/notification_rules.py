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
from tests.gui_e2e.testlib.playwright.timeouts import ANIMATION_TIMEOUT

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

    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.page.wait_for_url(
            url=re.compile(quote_plus("mode=notification_rule_quick_setup")), wait_until="load"
        )
        self.main_area.check_page_title(self.page_title)
        expect(self.overview_mode_button).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _get_row(self, row_name: str) -> Locator:
        return self.main_area.locator().get_by_role("group", name=row_name)

    # stage 1
    @property
    def host_events_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Host events")

    @property
    def _host_events_rows(self) -> Locator:
        return self._get_row("Host events").get_by_role("list").get_by_role("listitem")

    @property
    def _service_events_rows(self) -> Locator:
        return self._get_row("Service events").get_by_role("list").get_by_role("listitem")

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
    def _stage_two(self) -> Locator:
        return self.main_area.locator("li").filter(has_text="Filter for hosts")

    @property
    def _host_filters_button(self) -> Locator:
        return self._stage_two.get_by_role("button", name="Host filters")

    @property
    def _host_filters_dropdown(self) -> Locator:
        return self._stage_two.get_by_label("Host filters")

    @property
    def _hosts_row(self) -> Locator:
        return self._host_filters_dropdown.locator("tr").nth(4)

    @property
    def hosts_checkbox(self) -> Locator:
        return self._checkbox("Hosts", exact=True)

    def hosts_dropdown_list(self, index: int = 0) -> Locator:
        """Return locator corresponding to dropdown list consisting of host names.

        There can be multiple dropdown lists present.
        By default, the first one or left most one is addressed.
        """
        return self._hosts_row.locator("div.cmk-dropdown").nth(index)

    def select_host_from_dropdown_list(self, name: str, index: int = 0) -> Locator:
        """Return locator corresponding to a name present within the dropdown list of host names.

        There can be multiple dropdown lists present.
        By default, the first one or the left-most dropdown list is searched.
        """
        return self.hosts_dropdown_list(index).get_by_role("option", name=name)

    @property
    def _service_filters_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Service filters")

    @property
    def _exclude_services_checkbox(self) -> Locator:
        return self._checkbox("Exclude services", exact=True)

    @property
    def services_checkbox(self) -> Locator:
        return self._checkbox("Services", exact=True)

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

    def notification_effect_toggle(self, effect_label: str) -> Locator:
        return self.stage_three_locator.get_by_role("button", name=effect_label)

    def select_notification_effect(self, effect_label: str) -> None:
        effect_toggle = self.notification_effect_toggle(effect_label)
        expect(effect_toggle).to_be_visible()
        effect_toggle.click()

    def create_html_parameter_using_slide_in(self) -> None:
        """Open the slide-in window to initialize a new notifications parameter."""
        # `force=True` - prevents UI from sliding out of view during test runs
        create_button = self.stage_three_locator.get_by_role("button", name="Create")
        expect(
            create_button, message="Expected 'button' to create a new parameter to be visble!"
        ).to_be_visible()
        create_button.click(force=True)
        self.page.wait_for_timeout(ANIMATION_TIMEOUT)

    # stage 4
    @property
    def _stage_four_locator(self) -> Locator:
        return self.main_area.locator("li").filter(has_text="Recipient")

    @property
    def _add_recipient_button(self) -> Locator:
        return self._stage_four_locator.get_by_role("button", name="Add recipient")

    @property
    def _recipients_rows(self) -> Locator:
        return self._stage_four_locator.get_by_role("group", name="Select recipient").locator(
            "table > tr"
        )

    @property
    def _recipient_group(self) -> Locator:
        return self._stage_four_locator.get_by_role("group")

    def delete_recipient_button(self, index: int = 0) -> Locator:
        return self._recipients_rows.nth(index).get_by_role("button", name="Remove element")

    def select_recipient_dropdown(self, index: int = 0) -> Locator:
        return self._recipient_group.get_by_role("combobox").nth(index)

    def select_recipient_option(self, option: str) -> Locator:
        return self._recipient_group.get_by_role("option").filter(has_text=option)

    def add_new_entry_button(self) -> Locator:
        return self._recipient_group.get_by_role("button", name=" Add new entry")

    def select_user_dropdown(self) -> Locator:
        return self._recipient_group.locator("button").filter(has_text="Select user")

    @property
    def apply_and_create_another_rule_button(self) -> Locator:
        return self.main_area.locator().get_by_text("Apply & create another rule")

    def apply_and_create_another_rule(self) -> None:
        self.apply_and_create_another_rule_button.click()
        self.page.wait_for_url(
            url=re.compile(rf"{quote_plus('wato.py?mode=notification_rule_quick_setup')}$"),
            wait_until="load",
        )

    def delete_all_service_events(self) -> None:
        for _ in self._service_events_rows.all():
            self._service_events_rows.first.get_by_role("button", name="Remove element").click()

    # stage 6
    @property
    def description_text_field(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Description")

    @property
    def _disable_rule_button(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Disable rule")

    def _checkbox(self, name: str, exact: bool = False) -> Locator:
        ma = self.main_area.locator()
        return ma.get_by_role("checkbox").and_(ma.get_by_label(name, exact=exact))

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
        if self._host_filters_dropdown.get_attribute("aria-expanded") == "false":
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
        self.select_recipient_option(recipient_option_name).click()

    def add_recipient(
        self, index: int, recipient_option_name: str, recipient_value: str | None = None
    ) -> None:
        self.select_recipient_dropdown(index).click()
        self.select_recipient_option(recipient_option_name).click()
        if recipient_value:
            self.add_new_entry_button().click()
            self.select_user_dropdown().click()
            self.select_recipient_option(recipient_value).click()

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
        self.add_service_event(0, "State change", "Any", "WARN")

        logger.info("Apply service filter: '%s'", service)
        self.apply_services_filter(service)

        logger.info("Select default email parameter")
        self.select_email_parameter_dropdown.click()
        self.notification_method_option("Default").click()

        logger.info("Add recipient: '%s'", user)
        self.delete_all_recipients()
        self._add_recipient_button.click()
        self.add_recipient(0, "Specific users", user)

        logger.info("Add description: '%s'", description)
        self.description_text_field.fill(description)

        logger.info("Save the changes")
        self.apply_and_create_another_rule_button.click()

        self.validate_page()

        success_message = "Notification rule successfully edited!"
        expect(
            self.main_area.page_menu_popups,
            message=f"'{success_message}' message not displayed",
        ).to_contain_text(success_message)


class EditNotificationRule(BaseNotificationPage):
    """Represent the 'Edit notification rule' page.

    To navigate: `Setup > Notifications > Edit this notification rule`.
    """

    def __init__(
        self,
        page: Page,
        rule_position: int = 0,
        navigate_to_page: bool = True,
        navigate_to_notification_configuration: bool = True,
    ) -> None:
        self.rule_position = rule_position
        self.page_title = f"Edit notification rule {rule_position}"
        self._navigate_to_notification_configuration = navigate_to_notification_configuration
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        notification_configuration_page = NotificationConfiguration(
            self.page, navigate_to_page=self._navigate_to_notification_configuration
        )
        # The scrollbar interrupts the interaction with rule edit button -> -> collapse overview
        notification_configuration_page.collapse_notification_overview(True)
        notification_configuration_page.notification_rule_edit_button(self.rule_position).click()
        self.validate_page()


class AddNotificationRule(BaseNotificationPage):
    """Represent the 'Add notification rule' page.

    To navigate: `Setup > Notifications > Add notification rule`.
    """

    page_title = "Add notification rule"
    _go_to_next_stage_buttons_text = {
        1: "Next step: Specify host/services",
        2: "Next step: Notification method (plug-in)",
        3: "Next step: Recipient",
        4: "Next step: Sending conditions",
        5: "Next step: General properties",
        6: "Next step: Review all settings",
    }

    def navigate(self) -> None:
        notification_configuration_page = NotificationConfiguration(self.page)
        notification_configuration_page.add_notification_rule_button.click()
        self.validate_page()

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
        return self.editor_slide_in.get_by_role("group", name='Custom sender ("From")').get_by_role(
            "textbox", name="Display name"
        )

    @property
    def si_service_subject_checkbox(self) -> Locator:
        return self.editor_slide_in.get_by_role(
            "checkbox", name="Subject line for service notifications"
        )

    @property
    def si_service_subject_input(self) -> Locator:
        return self.editor_slide_in.get_by_role(
            "textbox", name="Subject line for service notifications"
        )

    @property
    def si_host_subject_checkbox(self) -> Locator:
        return self.editor_slide_in.get_by_role(
            "checkbox", name="Subject line for host notifications"
        )

    @property
    def si_host_subject_input(self) -> Locator:
        return self.editor_slide_in.get_by_role(
            "textbox", name="Subject line for host notifications"
        )
