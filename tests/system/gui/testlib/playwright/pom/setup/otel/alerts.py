#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Literal, override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

type AlertsColumn = Literal["Alert name", "Service match", "Thresholds"]


class Alerts(CmkPage):
    """Represent the page `Setup -> Events -> Alerts`."""

    page_title = "Alerts"
    main_menu_name = "Alerts"
    empty_state_text = "No alerts yet"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.click_and_wait_for_navigation(
            self.main_menu.setup_menu(self.main_menu_name, exact=True),
            frame_url=re.compile("mode=otel_alerts"),
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.add_alert_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def empty_state(self) -> Locator:
        return self.main_area.locator("div.no-config-bundles")

    @property
    def add_alert_button(self) -> Locator:
        return self.main_area.get_suggestion("Add alert")

    @property
    def alerts_table(self) -> Locator:
        return self.main_area.locator("table.data")

    def alert_row(self, alert_name: str) -> Locator:
        """The row of the alert named exactly `alert_name`; "Alert #1" does not match "Alert #10"."""
        return self.alerts_table.locator("tr.data").filter(
            has=self.page.get_by_role("cell", name=alert_name, exact=True)
        )

    def alert_cell(self, alert_name: str, column: AlertsColumn) -> Locator:
        """The `column` cell of the alert's row, e.g. "Regex: Latency.*" for "Service match".

        The table has no column IDs, so the column is found by the position of its header;
        "Thresholds" lists one line per bound, e.g. "Upper: warn/crit at 80/90".
        """
        header_cells = self.alerts_table.locator("th")
        expect(header_cells.first, "The alerts table has no header").to_be_visible()
        headers = [header.strip() for header in header_cells.all_inner_texts()]
        return self.alert_row(alert_name).locator("td").nth(headers.index(column))

    def edit_button(self, alert_name: str) -> Locator:
        return self.alert_row(alert_name).get_by_role("link", name="Edit this alert", exact=True)

    def delete_button(self, alert_name: str) -> Locator:
        return self.alert_row(alert_name).get_by_role("link", name="Delete this alert", exact=True)

    def delete_alert(self, alert_name: str) -> None:
        logger.info("Delete alert '%s'", alert_name)
        self.delete_button(alert_name).click()
        self.main_area.get_confirmation_popup_button("Delete").click()
        expect(
            self.alert_row(alert_name), f"The alert {alert_name!r} is still listed"
        ).to_have_count(0)
