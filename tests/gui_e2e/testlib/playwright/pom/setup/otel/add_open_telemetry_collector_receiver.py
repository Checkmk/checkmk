#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from re import Pattern
from typing import Any, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID, LocatorHelper
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.otel.open_telemetry_collector_receiver import (
    OpenTelemetryCollectorReceiver,
)

logger = logging.getLogger(__name__)


class AddOpenTelemetryCollectorReceiver(CmkPage):
    """Represent the page `Add OpenTelemetry Collector: Receiver`"""

    incorrect_form_error_message = "Cannot save the form because it contains errors."
    one_collector_per_site_error_detail = (
        "A site is allowed to be used in exactly one "
        "OpenTelemetry collector configuration: - '%s' is used in '%s'"
    )

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "Add OpenTelemetry Collector"
        super().__init__(page, navigate_to_page)
        self.new_password_slide_in = NewPasswordSlideIn(self.page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Add OpenTelemetry collector: Receiver` page."""
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
        expect(self.receiver_protocol_endpoint_checkbox("GRPC-based receiver")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def error_detail(self) -> Locator:
        return self.main_area.locator("div.cmk-inline-validation")

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

    def create_password_button(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("button", name="Create")

    def send_logs_to_event_console_checkbox(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role(
            "checkbox", name="Send log messages to event"
        )

    def resource_attribute_for_hostname_computation_textfield(self, receiver_type: str) -> Locator:
        return self._receiver(receiver_type).get_by_role("textbox", name="Resource attribute for")

    @staticmethod
    def click_on_last_locator(locator: Locator) -> None:
        target_index = locator.count() - 1
        locator.nth(target_index).click()

    @staticmethod
    def fill_last_locator(locator: Locator, value: str) -> None:
        target_index = locator.count() - 1
        locator.nth(target_index).fill(value)

    def add_new_password(self, receiver_type: str, password_data: dict[str, str]) -> None:
        self.create_password_button(receiver_type).click()
        expect(
            self.new_password_slide_in.title,
            "The slide-in didn't open after clicking on 'Create' button",
        ).to_be_visible()
        self.new_password_slide_in.password_id_textfield.fill(password_data["id"])
        self.new_password_slide_in.password_title_textfield.fill(password_data["title"])
        self.new_password_slide_in.password_textfield.fill(password_data["password"])
        self.new_password_slide_in.save_button.click()
        expect(
            self.new_password_slide_in.title,
            "The slide-in didn't collapse after clicking on 'Save' button",
        ).not_to_be_visible()

    def _fill_collector_receiver_properties(
        self,
        receiver_type: str,
        properties: dict[str, Any],
        new_password_data: list[dict[str, str]] | None = None,
    ) -> None:
        """Fill in receiver properties form and create new passwords if needed."""
        new_passwords_created = False
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
                if not new_passwords_created and new_password_data:
                    for password_data in new_password_data:
                        self.add_new_password(receiver_type, password_data)
                    new_passwords_created = True
                self.click_on_last_locator(self.password_dropdown(receiver_type))
                self.dropdown_option(
                    receiver_type, user_data["password"]["value"], exact=True
                ).click()
        if properties["endpoint"].get("event_console"):
            self.send_logs_to_event_console_checkbox(receiver_type).check()
            self.resource_attribute_for_hostname_computation_textfield(receiver_type).fill(
                properties["endpoint"]["event_console"]["host_name_resource_attribute_key"]
            )

    def fill_collector_configuration_form_and_save(
        self,
        collector_id: str,
        collector_title: str,
        site_id: str,
        grpc_receiver_properties: dict[str, Any] | None = None,
        grpc_password_data: list[dict[str, str]] | None = None,
        http_receiver_properties: dict[str, Any] | None = None,
        http_password_data: list[dict[str, str]] | None = None,
    ) -> None:
        logger.info("Fill in the 'OpenTelemetry Collector: Receiver' form")
        self.unique_id_textfield.fill(collector_id)
        self.title_textfield.fill(collector_title)
        self.site_restriction_checkbox(site_id).check()
        if grpc_receiver_properties:
            self._fill_collector_receiver_properties(
                "GRPC-based receiver",
                grpc_receiver_properties,
                grpc_password_data,
            )
        if http_receiver_properties:
            self._fill_collector_receiver_properties(
                "HTTP-based receiver",
                http_receiver_properties,
                http_password_data,
            )
        logger.info("Save the OpenTelemetry Collector configuration")
        self.save_configuration_button.click()


class NewPasswordSlideIn(LocatorHelper):
    """Represents 'Setup > Hosts > OpenTelemetry collector: Receiver
    > Add OpenTelemetry Collector: Receiver' slid-in for adding new password."""

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        if not selector:
            _loc = self._iframe_locator.get_by_label("New password")
        else:
            _loc = self._iframe_locator.locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        return _loc

    @property
    def title(self) -> Locator:
        return self.locator("h1[class*='cmk-heading']")

    @property
    def save_button(self) -> Locator:
        return self.locator().get_by_role("button", name="Save")

    @property
    def password_id_textfield(self) -> Locator:
        return self.locator().get_by_role("textbox", name="Unique ID")

    @property
    def password_title_textfield(self) -> Locator:
        return self.locator().get_by_role("textbox", name="Title")

    @property
    def password_textfield(self) -> Locator:
        return self.locator().get_by_role("textbox", name="Password")
