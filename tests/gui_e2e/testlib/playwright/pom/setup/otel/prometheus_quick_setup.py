#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class PrometheusQuickSetup(CmkPage):
    """Represent the page `Setup -> Telemetry -> Prometheus Quick Setup`."""

    page_title = "Prometheus Quick Setup"
    main_menu_name = "Prometheus Quick Setup"
    empty_state_text = "No Prometheus configuration yet"

    @override
    def navigate(self) -> None:
        logger.info(f"Navigate to '{self.page_title}' page")
        self.main_menu.setup_menu(self.main_menu_name, exact=True).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?mode=prometheus_overview")), wait_until="load"
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
        return self.configurations_table.locator(f"tr:has(td:has-text('{configuration_name}'))")

    @property
    def add_configuration_button(self) -> Locator:
        return self.main_area.get_suggestion("Add Prometheus configuration")


class AddPrometheusConfiguration(CmkPage):
    """Represent the Prometheus Quick Setup wizard"""

    page_title = "Add Prometheus configuration"
    success_message = "Prometheus configuration saved successfully."
    save_button_label = "Save Prometheus configuration"
    finish_button_label = "Finish & go to Activate changes"

    def __init__(self, page: Page, navigate_to_page: bool = True) -> None:
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        overview = PrometheusQuickSetup(self.page)
        overview.add_configuration_button.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?mode=create_prometheus_config")),
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

    # --- Step 1: configuration name + site ---

    @property
    def configuration_name_textfield(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Configuration name")

    @property
    def site_dropdown(self) -> Locator:
        return self.active_step.get_by_label("Site selection")

    def fill_configuration_name(self, configuration_name: str) -> None:
        self.configuration_name_textfield.fill(configuration_name)

    # --- Step 2: scraper details ---

    @property
    def job_name_textfield(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Job name")

    @property
    def metrics_path_textfield(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Metrics path")

    @property
    def address_textfield(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="IP address or host name")

    @property
    def port_textfield(self) -> Locator:
        return self.active_step.get_by_role("spinbutton", name="Port")

    @property
    def encryption_checkbox(self) -> Locator:
        return self.active_step.get_by_role("checkbox", name="Encrypt communication with TLS")

    def fill_scraper_details(
        self,
        *,
        job_name: str,
        metrics_path: str,
        address: str,
        port: int,
        encryption: bool,
    ) -> None:
        self.job_name_textfield.fill(job_name)
        self.metrics_path_textfield.fill(metrics_path)
        self.address_textfield.fill(address)
        self.port_textfield.fill(str(port))
        if encryption:
            self.encryption_checkbox.check()
        else:
            self.encryption_checkbox.uncheck()

    # --- Step 3: finalize ---

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
            url=re.compile(quote_plus("wato.py?mode=prometheus_overview")), wait_until="load"
        )
