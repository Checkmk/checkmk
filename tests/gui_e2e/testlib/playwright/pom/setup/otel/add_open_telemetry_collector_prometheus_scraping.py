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
from tests.gui_e2e.testlib.playwright.pom.setup.otel.open_telemetry_collector_prometheus_scraping import (
    OpenTelemetryCollectorPrometheusScraping,
)

logger = logging.getLogger(__name__)


class AddOpenTelemetryCollectorPrometheusScraping(CmkPage):
    """Represent the page `Add Prometheus scraping`"""

    incorrect_form_error_message = "Cannot save the form because it contains errors."
    one_collector_per_site_error_detail = (
        "A site is allowed to be used in exactly one "
        "OpenTelemetry collector configuration: <br>- '%s' is used in '%s'"
    )

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "Add Prometheus scraping"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Add OpenTelemetry collector: Prometheus scraping` page."""
        otel_collector_prom_scrape_page = OpenTelemetryCollectorPrometheusScraping(self.page)
        otel_collector_prom_scrape_page.add_open_telemetry_collector_configuration_btn.click()
        _url_pattern: str = quote_plus("mode=edit_otel_collectors_prom_scrape")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.unique_id_textfield).to_be_visible()
        expect(self.add_new_scraper_configuration_button)

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

    @property
    def add_new_scraper_configuration_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Add new scrape configuration")

    @property
    def job_name_textfield(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Job name")

    @property
    def scrape_interval_textfield(self) -> Locator:
        return self.main_area.locator().get_by_role("spinbutton", name="Scrape interval")

    @property
    def encrypt_communication_with_tls_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role(
            "checkbox", name="Encrypt communication with TLS"
        )

    @property
    def metrics_path_textfield(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Metrics path")

    @property
    def add_new_target_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Add new target")

    @property
    def ip_address_or_hostname_textfield(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="IP address or hostname")

    @property
    def port_textfield(self) -> Locator:
        return self.main_area.locator().get_by_role("spinbutton", name="Port")

    @staticmethod
    def fill_last_locator(locator: Locator, value: str) -> None:
        target_index = locator.count() - 1
        locator.nth(target_index).fill(value)

    def _fill_collector_scrape_properties(
        self,
        properties: dict[str, Any],
    ) -> None:
        self.add_new_scraper_configuration_button.click()
        self.job_name_textfield.fill(properties["job_name"])
        self.scrape_interval_textfield.fill(str(properties["scrape_interval"]))
        if properties["encryption"]:
            self.encrypt_communication_with_tls_checkbox.check()
        self.metrics_path_textfield.fill(properties["metrics_path"])
        for target in properties["targets"]:
            self.add_new_target_button.click()
            self.fill_last_locator(self.ip_address_or_hostname_textfield, target["address"])
            self.fill_last_locator(self.port_textfield, str(target["port"]))

    def fill_collector_configuration_form_and_save(
        self,
        collector_id: str,
        collector_title: str,
        site_id: str,
        collector_properties: dict[str, Any],
    ) -> None:
        logger.info("Fill in the 'OpenTelemetry Collector: Prometheus Scraping' form")
        self.unique_id_textfield.fill(collector_id)
        self.title_textfield.fill(collector_title)
        self.site_restriction_checkbox(site_id).check()
        self._fill_collector_scrape_properties(collector_properties)

        logger.info("Save the OpenTelemetry Collector configuration")
        self.save_configuration_button.click()
