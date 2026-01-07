#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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


class OpenTelemetryCollectorReceiver(CmkPage):
    """Represent the page `Setup -> Hosts -> OpenTelemetry Collector`"""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "OpenTelemetry Collector: Receiver (experimental)"
        self.main_menu_name = "OpenTelemetry Collector"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `OpenTelemetry Collector: Receiver (experimental)` page."""
        logger.info(f"Navigate to '{self.page_title}' page")

        self.main_menu.setup_menu(self.main_menu_name).click()
        _url_pattern: str = quote_plus("wato.py?mode=otel_collectors_receivers")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(
            self.add_open_telemetry_collector_receiver_configuration_btn,
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_open_telemetry_collector_receiver_configuration_btn(self) -> Locator:
        return self.main_area.get_suggestion("Add OpenTelemetry Collector receiver configuration")

    def collector_configuration_row(self, collector_id: str) -> Locator:
        return self.main_area.locator(f"tr:has(td:has-text('{collector_id}'))")

    def delete_collector_configuration_button(self, collector_id: str) -> Locator:
        return self.collector_configuration_row(collector_id).get_by_role(
            "link", name="Delete this OpenTelemetry Collector (Experimental)"
        )

    @property
    def delete_confirmation_button(self) -> Locator:
        return self.main_area.get_confirmation_popup_button("Delete")
