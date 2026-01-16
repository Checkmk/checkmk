#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from enum import StrEnum
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class ServiceState(StrEnum):
    OK = "OK"
    WARN = "WARN"
    CRIT = "CRIT"


class ServiceSearchPage(CmkPage):
    """Represent 'Service search' page.

    To navigate: 'Monitor > Overview > Service search'.
    """

    page_title: str = "Service search"

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        super().__init__(page=page, navigate_to_page=navigate_to_page, contain_filter_sidebar=True)

    def navigate(self) -> None:
        logger.info("Navigate to Monitor >> Overview >> %s", self.page_title)
        self.main_menu.monitor_menu("Service search").click()
        self.page.wait_for_url(url=re.compile(quote_plus("view_name=searchsvc")), wait_until="load")
        self.validate_page()

    def validate_page(self) -> None:
        logger.info("Validate that current page is %s page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.filter_sidebar.locator()).to_be_visible(timeout=5000)

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        mapping = DropdownListNameToID()
        setattr(mapping, "Services", "menu_service_multiple")
        return mapping

    def service_rows(self, host_name: str) -> Locator:
        """Return a locator for all rows corresponding to the services."""
        return self.main_area.locator(f"tr[class*='data']:has(td a[href*='{host_name}'])")

    def service_row(self, host_name: str, service_name: str) -> Locator:
        """Return a locator for a row corresponding to the service."""
        return self.main_area.locator(
            f"tr[class*='data']:has(td a[href*='{host_name}']):has(a:text-is('{service_name}'))"
        )

    def open_action_menu_button(self, host_name: str, service_name: str) -> Locator:
        return self.service_row(host_name, service_name).get_by_title("Open the action menu")

    def service_summary(self, host_name: str, service_name: str) -> Locator:
        return self.service_row(host_name, service_name).locator("td:nth-child(4)")

    def get_service_state(self, host_name: str, service_name: str) -> Locator:
        return self.service_row(host_name, service_name).locator("span.state_rounded_fill")

    @property
    def action_menu(self) -> Locator:
        return self.main_area.locator("div#popup_menu")

    def action_menu_item(self, item_name: str) -> Locator:
        return self.action_menu.get_by_text(item_name)

    @property
    def services_table(self) -> Locator:
        return self.main_area.locator("table[class*='data'] > tbody")

    def checked_column_cells(self, host_name: str) -> Locator:
        """Return value of time passed since last Check from 'Checked' column, for all the services."""
        return self.service_rows(host_name).locator("td:nth-child(6)")

    @property
    def reschedule_active_checks_popup(self) -> Locator:
        return self.main_area.locator("#popup_command_reschedule").filter(
            has_text="Reschedule active checks"
        )

    @property
    def reschedule_active_checks_confirmation_window(self) -> Locator:
        return self.main_area.locator().get_by_label("Reschedule active checks immediately")

    @property
    def reschedule_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Reschedule")

    @property
    def spread_over_minutes_textbox(self) -> Locator:
        return self.reschedule_active_checks_popup.get_by_role("textbox")

    @property
    def back_to_view_link(self) -> Locator:
        return self.main_area.locator().get_by_role("link", name="Back to view")

    def reschedule_check(self, host_name: str, check_name: str) -> None:
        self.open_action_menu_button(host_name, check_name).click()
        self.action_menu_item("Reschedule check").click()
        self.page.wait_for_load_state("load")

    def wait_for_check_status_update(
        self, host_name: str, service_name: str, expected_state: ServiceState, attempts: int = 5
    ) -> None:
        """Wait for the service summary to contain the expected string.

        After applying a new rule, the service summary should be updated accordingly.
        This process may take some time, so an attempt is made to check the service summary and
        reschedule the check if the expected string is not found.
        """
        for _ in range(attempts):
            logger.debug("Attempt-%d", _ + 1)
            try:
                expect(self.get_service_state(host_name, service_name)).to_have_text(expected_state)
            except AssertionError:
                self.reschedule_check(host_name, "Check_MK")
            else:
                return

        raise AssertionError(
            f"Expected string '{expected_state}' not found in '{service_name}' service summary "
            f"after {attempts} attempts"
        )
