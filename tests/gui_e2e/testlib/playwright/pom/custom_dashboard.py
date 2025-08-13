#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.pom.dashboard import BaseDashboard

logger = logging.getLogger(__name__)


class CustomDashboard(BaseDashboard):
    """Represents a custom dashboard."""

    def __init__(
        self,
        page: Page,
        page_title: str,
        navigate_to_page: bool = True,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ):
        self.page_title = page_title
        super().__init__(
            page,
            navigate_to_page,
            timeout_assertions,
            timeout_navigation,
        )

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s'", self.page_title)
        self.go_to_edit_dashboards_page()
        self.main_area.locator(
            "//h3[@class='table'][text()='Customized']/following-sibling::table[1]"
        ).get_by_role("link", name=self.page_title, exact=True).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)
        expect(
            self.main_area.locator("div#dashboard"),
            message=f"Dashboard '{self.page_title}' is not loaded",
        ).to_be_visible()

    @property
    def enter_layout_mode_icon(self) -> Locator:
        return self.main_area.locator().get_by_role("link", name="Enter layout mode")

    @property
    def leave_layout_mode_icon(self) -> Locator:
        return self.main_area.locator().get_by_role("link", name="Leave layout mode")

    @property
    def delete_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']")

    @property
    def delete_confirmation_button(self) -> Locator:
        return self.delete_confirmation_window.get_by_role("button", name="Yes")

    def go_to_edit_dashboards_page(self) -> None:
        self.main_menu.customize_menu("Dashboards").click()
        self.page.wait_for_url(url=re.compile("edit_dashboards.py$"), wait_until="load")

    def _wait_layout_mode(self, enabled: bool) -> None:
        self.page.wait_for_url(
            url=re.compile(f"{quote_plus(f'edit={1 if enabled else 0}')}$"), wait_until="load"
        )

    def enter_layout_mode(self) -> None:
        """Enter the dashboard layout mode."""
        self.enter_layout_mode_icon.click()
        self._wait_layout_mode(enabled=True)

    def leave_layout_mode(self) -> None:
        """Leave the dashboard layout mode."""
        self.leave_layout_mode_icon.click()
        self._wait_layout_mode(enabled=False)

    def delete(self) -> None:
        self.go_to_edit_dashboards_page()
        custom_dashboard_link = (
            self.main_area.locator().get_by_role("link", name=self.page_title, exact=True).first
        )
        custom_dashboard_row = self.main_area.locator("tr", has=custom_dashboard_link)
        custom_dashboard_row.get_by_role("link", name="Delete").click()
        self.main_area.get_confirmation_popup_button("Delete").click()

        expect(
            self.main_area.locator("div.success"),
            message=f"Dashboard '{self.page_title}' is not deleted",
        ).to_have_text("Your dashboard has been deleted.")
