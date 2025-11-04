#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Any, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.otel.open_telemetry_collector_receiver import (
    OpenTelemetryCollectorReceiver,
)

logger = logging.getLogger(__name__)


class AddOpenTelemetryCollectorReceiver(CmkPage):
    """Represent the page `Add OpenTelemetry collector: Receiver (experimental)`"""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "Add OpenTelemetry collector: Receiver (experimental)"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Add OpenTelemetry collector: Receiver (experimental)` page."""
        otel_collector_receiver_page = OpenTelemetryCollectorReceiver(self.page)
        otel_collector_receiver_page.add_open_telemetry_collector_receiver_configuration_btn.click()
        _url_pattern: str = quote_plus("mode=edit_otel_collectors_receiver")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.unique_id_textfield).to_be_visible()
        expect(self.receiver_protocol_endpoint_checkbox("Receiver protocol GRPC")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_configuration_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def unique_id_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Unique ID")

    @property
    def title_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Title")

    @property
    def comment_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Comment")

    @property
    def documentation_url_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Documentation URL")

    def site_restriction_checkbox(self, site_name: str) -> Locator:
        return self.main_area.locator().get_by_label("Site restriction").get_by_text(site_name)

    def _receiver(self, self_receiver_type: str) -> Locator:
        return self.main_area.locator().get_by_label(self_receiver_type)

    def receiver_protocol_endpoint_checkbox(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("checkbox", name="Endpoint")

    def encrypt_communication_with_tls_checkbox(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_label("Encrypt communication with TLS")

    def ip_address_or_hostname_textfield(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("textbox", name="IP address or hostname")

    def port_textfield(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("spinbutton", name="Port")

    def authentication_method_dropdown(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_label("Authentication method")

    def dropdown_option(self, receiver_type: str, option: str, exact: bool = False) -> Locator:
        return self._receiver(receiver_type).get_by_role("option", name=option, exact=exact)

    def add_new_credentials_button(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("button", name="Add new credentials")

    def username_textfield(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_label("Username")

    def password_dropdown(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("combobox", name="Password")

    def add_new_host_name_computation_rule_button(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("button", name="Add new rule")

    def add_new_field_button(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("button", name="Add new field")

    def host_name_computation_field_type_dropdown(self, receiver_type: str) -> Locator:
        return (
            self._receiver(receiver_type)
            .get_by_role("combobox")
            .get_by_text(re.compile(r"(Value of attribute|Literal string)", re.IGNORECASE))
        )

    def value_of_attribute_dropdown(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).locator("button.cmk-dropdown-button--group-start")

    def value_of_attribute_filter(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_label("filter")

    def literal_string_textfield(self, receiver_type: str) -> Locator:
        return (
            self._receiver(receiver_type)
            .get_by_text("Host name computation The")
            .locator("input[type='text']")
        )

    def send_logs_to_event_console_checkbox(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role(
            "checkbox", name="Send log messages to event"
        )

    @staticmethod
    def click_on_last_locator(locator: Locator) -> None:
        target_index = locator.count() - 1
        locator.nth(target_index).click()

    @staticmethod
    def fill_last_locator(locator: Locator, value: str) -> None:
        target_index = locator.count() - 1
        locator.nth(target_index).fill(value)

    def fill_collector_receiver_properties(
        self,
        receiver_type: str,
        properties: dict[str, Any],
    ) -> None:
        logger.info(
            "Fill in the 'OpenTelemetry Collector: Receiver (Experimental) properties' form"
        )
        self.receiver_protocol_endpoint_checkbox(receiver_type).check()
        if properties["endpoint"]["encryption"]:
            self.encrypt_communication_with_tls_checkbox(receiver_type).check()
        self.ip_address_or_hostname_textfield(receiver_type).fill(properties["endpoint"]["address"])
        self.port_textfield(receiver_type).fill(properties["endpoint"]["port"])
        if properties["endpoint"]["auth"]["type"] != "none":
            self.authentication_method_dropdown(receiver_type).click()
            self.dropdown_option(receiver_type, "Basic Authentication").click()
            for user_data in properties["endpoint"]["auth"]["userlist"]:
                self.add_new_credentials_button(receiver_type).click()
                self.fill_last_locator(
                    self.username_textfield(receiver_type), user_data["username"]
                )
                self.click_on_last_locator(self.password_dropdown(receiver_type))
                self.dropdown_option(
                    receiver_type, user_data["password"]["value"], exact=True
                ).click()

        for host_name_rule in properties["endpoint"]["host_name_rules"]:
            self.add_new_host_name_computation_rule_button(receiver_type).click()
            for host_name_field in host_name_rule:
                self.click_on_last_locator(self.add_new_field_button(receiver_type))
                if host_name_field["type"] != "key":  # to remove
                    self.click_on_last_locator(
                        self.host_name_computation_field_type_dropdown(receiver_type)
                    )
                if host_name_field["type"] == "key":
                    # self.dropdown_option(receiver_type, "Value of attribute").click() to uncomment
                    if host_name_field["value"] != "service.name":  # to remove
                        self.click_on_last_locator(self.value_of_attribute_dropdown(receiver_type))
                        self.fill_last_locator(
                            self.value_of_attribute_filter(receiver_type),
                            host_name_field["value"],
                        )
                        self.dropdown_option(receiver_type, host_name_field["value"]).click()
                elif host_name_field["type"] == "free":
                    self.dropdown_option(receiver_type, "Literal string").click()
                    self.fill_last_locator(
                        self.literal_string_textfield(receiver_type), host_name_field["value"]
                    )
                else:
                    raise ValueError(f"Unknown host name field type: {host_name_field['type']}")
        if properties["endpoint"].get("export_to_syslog"):
            self.send_logs_to_event_console_checkbox(receiver_type).check()
