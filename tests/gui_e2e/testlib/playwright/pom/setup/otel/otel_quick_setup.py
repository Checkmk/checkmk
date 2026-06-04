#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Literal, override

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.otel.new_password_slide_in import (
    NewPasswordSlideIn,
)

logger = logging.getLogger(__name__)

ProtocolTab = Literal["grpc", "http"]


class OTelQuickSetup(CmkPage):
    """Represent the page `Setup -> Telemetry -> OpenTelemetry Quick Setup`."""

    page_title = "OpenTelemetry Quick Setup"
    main_menu_name = "OpenTelemetry Quick Setup"
    empty_state_text = "No OpenTelemetry configuration yet"

    @override
    def navigate(self) -> None:
        logger.info(f"Navigate to '{self.page_title}' page")
        self.main_menu.setup_menu(self.main_menu_name, exact=True).click()
        self.page.wait_for_url(
            url=re.compile(re.escape("wato.py?mode=otel_overview")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def empty_state(self) -> Locator:
        return self.main_area.locator("div.no-config-bundles")

    @property
    def configurations_table(self) -> Locator:
        return self.main_area.locator("table.data")

    def configuration_row(self, configuration_name: str) -> Locator:
        return self.configurations_table.get_by_role("row").filter(has_text=configuration_name)

    @property
    def add_configuration_button(self) -> Locator:
        return self.main_area.get_suggestion("Add OpenTelemetry configuration")

    def edit_configuration_button(self, configuration_name: str) -> Locator:
        return self.configuration_row(configuration_name).get_by_role(
            "link", name="Edit", exact=True
        )

    def delete_configuration_button(self, configuration_name: str) -> Locator:
        return self.configuration_row(configuration_name).get_by_role(
            "link", name="Delete this configuration"
        )

    @property
    def delete_confirmation_button(self) -> Locator:
        return self.main_area.get_confirmation_popup_button("Delete")


class EditOTelConfiguration(CmkPage):
    """Represent the OpenTelemetry Quick Setup configuration edit page.

    Reached via the 'Edit' button on the `OTelQuickSetup` overview (`mode=edit_otel_config`).
    It renders the bundle component tiles ('OpenTelemetry Collector', 'Dynamic host management')
    on top of the configuration properties form.
    """

    page_title = "Edit configuration"

    def __init__(self, page: Page, configuration_name: str, navigate_to_page: bool = True) -> None:
        self._configuration_name = configuration_name
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        overview = OTelQuickSetup(self.page)
        overview.edit_configuration_button(self._configuration_name).click()
        # Don't wait on the parent-frame URL here: its sync with the iframe can break after a
        # site restart, making wait_for_url flaky. Validate the rendered iframe content instead.
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        expect(self.otel_collector_tile).to_be_visible()
        expect(self.dynamic_host_management_tile).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def _tiles(self) -> Locator:
        return self.main_area.locator("div.mainmenu")

    @property
    def otel_collector_tile(self) -> Locator:
        return self._tiles.get_by_role("link").filter(has_text="OpenTelemetry Collector")

    @property
    def dynamic_host_management_tile(self) -> Locator:
        return self._tiles.get_by_role("link").filter(has_text="Dynamic host management")


class AddOTelConfiguration(CmkPage):
    """Represent the OpenTelemetry Quick Setup wizard"""

    page_title = "Add OpenTelemetry configuration"
    success_message = "OpenTelemetry configuration saved successfully."
    save_button_label = "Save OpenTelemetry configuration"
    finish_button_label = "Finish & go to Activate changes"

    def __init__(self, page: Page, navigate_to_page: bool = True) -> None:
        super().__init__(page, navigate_to_page)
        self.password_slide_in = NewPasswordSlideIn(self.main_area.locator())

    @override
    def navigate(self) -> None:
        overview = OTelQuickSetup(self.page)
        overview.add_configuration_button.click()
        self.page.wait_for_url(
            url=re.compile(re.escape("wato.py?mode=create_otel_config")),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.wizard_root).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def wizard_root(self) -> Locator:
        return self.main_area.locator("ol.cmk-wizard")

    @property
    def active_step(self) -> Locator:
        return self.wizard_root.locator('li[aria-current="step"]')

    @property
    def next_step_button(self) -> Locator:
        return self.active_step.get_by_role("button", name="Next step")

    # --- Step 1: general configuration properties ---

    @property
    def configuration_name_textfield(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Configuration name")

    @property
    def site_dropdown(self) -> Locator:
        return self.active_step.get_by_label("Site selection")

    def fill_configuration_name(self, configuration_name: str) -> None:
        self.configuration_name_textfield.fill(configuration_name)

    # --- Step 2: collector receivers (GRPC + HTTP tabs) ---

    _TAB_LABELS: dict[ProtocolTab, str] = {"grpc": "GRPC", "http": "HTTP"}
    _ENABLE_LABELS: dict[ProtocolTab, str] = {
        "grpc": "Enable the GRPC-based OTLP receiver",
        "http": "Enable the HTTP-based OTLP receiver",
    }

    def tab(self, protocol: ProtocolTab) -> Locator:
        return self.active_step.get_by_role("tab", name=self._TAB_LABELS[protocol], exact=True)

    @property
    def _active_tab_panel(self) -> Locator:
        return self.active_step.locator('[role="tabpanel"][data-state="active"]')

    def switch_to_tab(self, protocol: ProtocolTab) -> None:
        self.tab(protocol).click()

    def enable_protocol_checkbox(self, protocol: ProtocolTab) -> Locator:
        return self._active_tab_panel.get_by_role(
            "checkbox", name=self._ENABLE_LABELS[protocol], exact=True
        )

    @property
    def socket_address_dropdown(self) -> Locator:
        return self._active_tab_panel.get_by_label("Socket address to listen on")

    @property
    def address_textfield(self) -> Locator:
        return self._active_tab_panel.get_by_role("textbox", name="IP address or host name")

    @property
    def port_textfield(self) -> Locator:
        return self._active_tab_panel.get_by_role("spinbutton", name="Port")

    @property
    def authentication_method_dropdown(self) -> Locator:
        return self._active_tab_panel.get_by_label("Authentication method")

    @property
    def username_textfield(self) -> Locator:
        return self._active_tab_panel.get_by_role("textbox", name="Username")

    @property
    def password_dropdown(self) -> Locator:
        return self._active_tab_panel.get_by_label("Password", exact=True)

    @property
    def create_password_button(self) -> Locator:
        return self._active_tab_panel.get_by_role("button", name="Create", exact=True)

    @property
    def encryption_checkbox(self) -> Locator:
        return self._active_tab_panel.get_by_role("checkbox", name="Encrypt communication with TLS")

    @property
    def event_console_checkbox(self) -> Locator:
        return self._active_tab_panel.get_by_role(
            "checkbox", name="Send log messages to event console"
        )

    @property
    def resource_attribute_textfield(self) -> Locator:
        return self._active_tab_panel.get_by_role(
            "textbox", name="Resource attribute for host name lookup"
        )

    def select_dropdown_option(self, dropdown: Locator, option_name: str) -> None:
        dropdown.click()
        self.main_area.locator().get_by_role("option", name=option_name, exact=True).click()

    def fill_endpoint(self, address: str, port: int) -> None:
        self.select_dropdown_option(self.socket_address_dropdown, "Custom")
        self.address_textfield.fill(address)
        self.port_textfield.fill(str(port))

    def select_basic_authentication(self) -> None:
        self.select_dropdown_option(self.authentication_method_dropdown, "Basic authentication")

    def select_password(self, option_text: str) -> None:
        self.password_dropdown.click()
        self.main_area.locator().get_by_role(
            "option", name=re.compile(rf"^{re.escape(option_text)}")
        ).click()

    def set_encryption(self, enabled: bool) -> None:
        if enabled:
            self.encryption_checkbox.check()
        else:
            self.encryption_checkbox.uncheck()

    def enable_event_console(self, resource_attribute: str) -> None:
        self.event_console_checkbox.check()
        self.resource_attribute_textfield.fill(resource_attribute)

    # --- Step 3: instrumentation snippets ---

    @property
    def instrumentation_sdk_tab(self) -> Locator:
        return self.active_step.get_by_role("tab", name="SDKs", exact=True)

    @property
    def code_blocks(self) -> Locator:
        return self.active_step.locator("pre")

    @property
    def copy_buttons(self) -> Locator:
        return self.active_step.locator("button.copy_button")

    @property
    def sdk_command_text(self) -> Locator:
        return self.active_step.locator("div.mode-otel-configure-instrumentation__code-text")

    # --- Step 4: finalize ---

    @property
    def finalize_items_list(self) -> Locator:
        return self.active_step.locator("ul.mode-otel-finalize-configuration__items")

    @property
    def success_alert(self) -> Locator:
        return self.active_step.get_by_text(self.success_message)

    @property
    def save_button(self) -> Locator:
        return self.active_step.get_by_role("button", name=self.save_button_label)

    @property
    def finish_button(self) -> Locator:
        return self.active_step.get_by_role("button", name=self.finish_button_label)

    def wait_for_finalize_success(self, timeout_ms: int = 30_000) -> None:
        expect(self.finish_button).to_be_visible(timeout=timeout_ms)
        expect(self.finish_button).to_be_enabled(timeout=timeout_ms)
        expect(self.success_alert).to_be_visible(timeout=timeout_ms)
        expect(self.finalize_items_list).to_have_attribute("aria-busy", "false", timeout=timeout_ms)

    def finish_and_go_to_activate_changes(self) -> None:
        self.finish_button.click()
        self.page.wait_for_url(
            url=re.compile(re.escape("wato.py?mode=otel_overview")), wait_until="load"
        )
