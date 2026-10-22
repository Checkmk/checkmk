#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class CustomServices(CmkPage):
    """Represent the page `Setup -> Telemetry -> Custom Services`."""

    page_title = "Custom Services"
    main_menu_name = "Custom Services"
    empty_state_text = "No custom services yet"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.click_and_wait_for_navigation(
            self.main_menu.setup_menu(self.main_menu_name, exact=True),
            frame_url=re.compile("mode=otel_custom_services"),
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.add_custom_service_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def empty_state(self) -> Locator:
        return self.main_area.locator("div.no-config-bundles")

    @property
    def add_custom_service_button(self) -> Locator:
        return self.main_area.get_suggestion("Add custom service")

    @property
    def services_table(self) -> Locator:
        return self.main_area.locator("table.data")

    def service_row(self, service_name: str) -> Locator:
        return self.services_table.locator("tr.data", has_text=service_name)

    def edit_button(self, service_name: str) -> Locator:
        return self.service_row(service_name).get_by_role(
            "link", name="Edit this custom service", exact=True
        )

    def delete_button(self, service_name: str) -> Locator:
        return self.service_row(service_name).get_by_role(
            "link", name="Delete this custom service", exact=True
        )

    def delete_custom_service(self, service_name: str) -> None:
        logger.info("Delete custom service '%s'", service_name)
        self.delete_button(service_name).click()
        self.main_area.get_confirmation_popup_button("Delete").click()
        expect(
            self.service_row(service_name), f"The custom service {service_name!r} is still listed"
        ).to_have_count(0)
