# !/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class ServiceSearchPage(CmkPage):
    """Represent 'Service search' page.

    To navigate: 'Monitor > Overview > Service search'.
    """

    page_title: str = "Service search"

    def navigate(self) -> None:
        logger.info("Navigate to Monitor >> Overview >> %s", self.page_title)
        self.main_menu.monitor_menu("Service search").click()
        self.page.wait_for_url(url=re.compile(quote_plus("view_name=searchsvc")), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is %s page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.filter_sidebar).to_be_visible(timeout=5000)

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def service_rows(self) -> Locator:
        """Return a locator for all rows corresponding to the services."""
        return self.main_area.locator("tr[class*='data']")

    @property
    def services_table(self) -> Locator:
        return self.main_area.locator("table[class*='data'] > tbody")

    @property
    def checked_column_cells(self) -> Locator:
        """Return value of time passed since last Check from 'Checked' column, for all the services."""
        return self.service_rows.locator("td:nth-child(6)")

    @property
    def filter_sidebar(self) -> Locator:
        return self.main_area.locator("div#popup_filters")

    @property
    def apply_filters_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Apply filters")

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
