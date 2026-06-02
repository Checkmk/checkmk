#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.otel.add_open_telemetry_collector_prometheus_scraping import (
    AddOpenTelemetryCollectorPrometheusScraping,
)

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

    def edit_button(self, configuration_name: str) -> Locator:
        return self.configuration_row(configuration_name).get_by_role(
            "link", name="Edit", exact=True
        )

    @property
    def add_configuration_button(self) -> Locator:
        return self.main_area.get_suggestion("Add Prometheus configuration")


class AddPrometheusQuickSetupConfiguration(CmkPage):
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
        PrometheusQuickSetup(self.page, navigate_to_page=False)


class EditPrometheusQuickSetupConfiguration(CmkPage):
    """Represent the Prometheus Quick Setup edit page"""

    def __init__(
        self, page: Page, configuration_name: str | None = None, navigate_to_page: bool = True
    ) -> None:
        self._configuration_name = configuration_name
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        assert self._configuration_name is not None, (
            "A configuration name is required to navigate to the Prometheus configuration edit page"
        )
        overview = PrometheusQuickSetup(self.page)
        overview.edit_button(self._configuration_name).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is the Prometheus configuration edit page")
        expect(self.prometheus_scraper_button).to_be_visible()
        expect(self.dynamic_host_management_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def bundle_links(self) -> Locator:
        return self.main_area.locator("div.mainmenu")

    @property
    def prometheus_scraper_button(self) -> Locator:
        return self.bundle_links.get_by_role("link", name="Prometheus scraper")

    @property
    def dynamic_host_management_button(self) -> Locator:
        return self.bundle_links.get_by_role("link", name="Dynamic host management")

    @property
    def configuration_name_textfield(self) -> Locator:
        return (
            self.main_area.locator("tr")
            .filter(has_text="Configuration name")
            .get_by_role("textbox")
        )

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    def rename_configuration(self, new_name: str) -> None:
        self.configuration_name_textfield.fill(new_name)
        self.save_button.click()


class EditPrometheusQuickSetupScraper(AddOpenTelemetryCollectorPrometheusScraping):
    """Represent the Prometheus scraper edit page when it is part of the Prometheus Quick Setup."""

    def __init__(
        self, page: Page, configuration_name: str | None = None, navigate_to_page: bool = True
    ) -> None:
        self._configuration_name = configuration_name
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        assert self._configuration_name is not None, (
            "A configuration name is required to navigate to the Prometheus scraper edit page"
        )
        edit_page = EditPrometheusQuickSetupConfiguration(self.page, self._configuration_name)
        edit_page.prometheus_scraper_button.click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is the Prometheus scraper edit page")
        expect(self.encrypt_communication_with_tls_checkbox).to_be_visible()

    @property
    def quick_setup_warning(self) -> Locator:
        return self.main_area.locator("div.warning_container")

    def save(self) -> None:
        self.save_configuration_button.click()
